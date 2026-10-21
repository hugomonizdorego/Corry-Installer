/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014-2015 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2015 Anke Boersma <demm@kaosx.us>
 *   SPDX-FileCopyrightText: 2017-2019 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "WelcomePage.h"

#include "checker/CheckerContainer.h"
#include "ui_WelcomePage.h"

#include "Branding.h"
#include "CalamaresAbout.h"
#include "CalamaresConfig.h"
#include "CalamaresVersion.h"
#include "Config.h"
#include "Settings.h"
#include "ViewManager.h"

#include "modulesystem/ModuleManager.h"
#include "modulesystem/RequirementsModel.h"
#include "utils/Gui.h"
#include "utils/Logger.h"
#include "utils/NamedEnum.h"
#include "utils/Retranslator.h"

#include <QApplication>
#include <QBoxLayout>
#include <QComboBox>
#include <QDesktopServices>
#include <QFile>
#include <QFocusEvent>
#include <QLabel>
#include <QMessageBox>
#include <QPushButton>
#ifdef WITH_QML
#include <QQmlContext>
#include <QQmlError>
#include <QQuickWidget>
#endif

WelcomePage::WelcomePage( Config* config, QWidget* parent )
    : QWidget( parent )
    , ui( new Ui::WelcomePage )
    , m_checkingWidget( new CheckerContainer( config, this ) )
    , m_languages( nullptr )
    , m_conf( config )
{
    using Branding = Calamares::Branding;

    const int defaultFontHeight = Calamares::defaultFontHeight();
    ui->setupUi( this );

    // insert system-check widget below welcome text
    const int welcome_text_idx = ui->verticalLayout->indexOf( ui->mainText );
    ui->verticalLayout->insertWidget( welcome_text_idx + 1, m_checkingWidget );

    // insert optional logo banner image above welcome text
    QString bannerPath = Branding::instance()->imagePath( Branding::ProductBanner );
    if ( !bannerPath.isEmpty() )
    {
        // If the name is not empty, the file exists -- Branding checks that at startup
        QPixmap bannerPixmap = QPixmap( bannerPath );
        if ( !bannerPixmap.isNull() )
        {
            QLabel* bannerLabel = new QLabel;
            bannerLabel->setPixmap( bannerPixmap );
            bannerLabel->setMinimumHeight( 64 );
            bannerLabel->setAlignment( Qt::AlignCenter );
            ui->aboveTextSpacer->changeSize( 20, defaultFontHeight );  // Shrink it down
            ui->aboveTextSpacer->invalidate();
            ui->verticalLayout->insertSpacing( welcome_text_idx, defaultFontHeight );
            ui->verticalLayout->insertWidget( welcome_text_idx, bannerLabel );
        }
    }

    initLanguages();

    CALAMARES_RETRANSLATE_SLOT( &WelcomePage::retranslate );

    connect( Calamares::ModuleManager::instance(),
             &Calamares::ModuleManager::requirementsComplete,
             m_checkingWidget,
             &CheckerContainer::requirementsComplete );
    connect( Calamares::ModuleManager::instance()->requirementsModel(),
             &Calamares::RequirementsModel::progressMessageChanged,
             m_checkingWidget,
             &CheckerContainer::requirementsProgress );
}

void
WelcomePage::setCorryPage( const QString& page )
{
    if ( Calamares::Branding::instance()->componentName() != QStringLiteral( "corry" ) || page.isEmpty() )
    {
        return;
    }
    m_corryPage = page;
    ui->horizontalLayout->setContentsMargins( 24, 20, 24, 20 );
    ui->horizontalLayout->setSpacing( 32 );
    ui->mainText->setAlignment( Qt::AlignLeft | Qt::AlignVCenter );
    QFont titleFont = ui->mainText->font();
    titleFont.setPointSize( 30 );
    titleFont.setBold( true );
    ui->mainText->setFont( titleFont );
    ui->languageIcon->hide();
    // Group title, text and controls in the vertical middle, left aligned.
    ui->mainText->setSizePolicy( QSizePolicy::Preferred, QSizePolicy::Maximum );
    ui->aboveTextSpacer->changeSize( 0, 0, QSizePolicy::Minimum, QSizePolicy::Expanding );
    for ( auto* spacer : { ui->horizontalSpacer, ui->horizontalSpacer_3, ui->horizontalSpacer_4 } )
    {
        spacer->changeSize( 0, 0, QSizePolicy::Fixed, QSizePolicy::Minimum );
    }
    ui->verticalLayout->setSpacing( 18 );
    ui->verticalLayout->addStretch( 1 );
    auto* introduction = new QLabel( this );
    introduction->setWordWrap( true );
    introduction->setObjectName( "corryHint" );
    ui->verticalLayout->insertWidget( ui->verticalLayout->indexOf( ui->mainText ) + 1, introduction );

    if ( page == QStringLiteral( "greeting" ) )
    {
        // The greeting page only welcomes and offers the language; the system
        // check has its own page next.
        ui->verticalLayout->removeWidget( m_checkingWidget );
        m_checkingWidget->hide();
        ui->horizontalLayout->addWidget( welcomeMedia(), 1 );
        ui->horizontalLayout->setStretch( 0, 1 );
        CALAMARES_RETRANSLATE( introduction->setText(
            tr( "Thank you for choosing %1. Corry will guide you one step at a time: first a quick check of this "
                "computer, then your location, keyboard, disk and account. Nothing on your disks changes until you "
                "confirm the final review." )
                .arg( Calamares::Branding::instance()->shortProductName() ) ); );
        return;
    }

    // System check page: requirements, internet status and the recommendation.
    for ( QWidget* w : { static_cast< QWidget* >( ui->languageWidget ),
                         static_cast< QWidget* >( ui->supportButton ),
                         static_cast< QWidget* >( ui->knownIssuesButton ),
                         static_cast< QWidget* >( ui->releaseNotesButton ),
                         static_cast< QWidget* >( ui->donateButton ) } )
    {
        w->hide();
    }
    m_hideButtons = true;
    auto* card = new QWidget( this );
    card->setObjectName( "corryNetworkCard" );
    auto* row = new QHBoxLayout( card );
    auto* advice = new QLabel( card );
    advice->setWordWrap( true );
    auto* recheck = new QPushButton( card );
    recheck->setObjectName( "corryRecheckButton" );
    row->addWidget( advice, 1 );
    row->addWidget( recheck );
    ui->verticalLayout->insertWidget( ui->verticalLayout->indexOf( m_checkingWidget ) + 1, card );
    connect( recheck, &QPushButton::clicked, this, [] { Calamares::ModuleManager::instance()->checkRequirements(); } );
    CALAMARES_RETRANSLATE(
        introduction->setText( tr( "Corry checks that this computer can run %1 and whether it is online." )
                                   .arg( Calamares::Branding::instance()->shortProductName() ) );
        advice->setText( tr( "<b>An internet connection is recommended.</b> When online, Corry repairs broken "
                             "packages and installs the latest updates while installing, so the new system starts "
                             "clean and up to date. Without internet, everything is installed from the "
                             "installation media. Connect now, then press Check again." ) );
        recheck->setText( tr( "Check again" ) ); );
}

QWidget*
WelcomePage::welcomeMedia()
{
    const QString poster = Calamares::Branding::instance()->imagePath( Calamares::Branding::ProductWelcome );
#ifdef WITH_QML
    const QString qml = Calamares::Branding::instance()->componentDirectory() + QStringLiteral( "/welcome-media.qml" );
    if ( QFile::exists( qml ) )
    {
        // A looping, muted product video with the welcome image as poster.
        auto* view = new QQuickWidget( this );
        view->setObjectName( "corryWelcomeMedia" );
        view->setResizeMode( QQuickWidget::SizeRootObjectToView );
        view->setClearColor( Qt::transparent );
        view->setAttribute( Qt::WA_AlwaysStackOnTop );
        view->rootContext()->setContextProperty( QStringLiteral( "corryPoster" ), QUrl::fromLocalFile( poster ) );
        view->setSource( QUrl::fromLocalFile( qml ) );
        view->setMinimumSize( 320, 200 );
        if ( view->status() != QQuickWidget::Error )
        {
            return view;
        }
        cWarning() << "Corry welcome media could not be loaded" << view->errors();
        view->deleteLater();
    }
#endif
    auto* image = new QLabel( this );
    image->setAlignment( Qt::AlignCenter );
    image->setPixmap( QPixmap( poster ).scaled( 560, 360, Qt::KeepAspectRatio, Qt::SmoothTransformation ) );
    return image;
}

void
WelcomePage::init()
{
    //setup the url buttons
    if ( !m_hideButtons )
    {
        setupButton( WelcomePage::Button::Support, m_conf->supportUrl() );
        setupButton( WelcomePage::Button::KnownIssues, m_conf->knownIssuesUrl() );
        setupButton( WelcomePage::Button::ReleaseNotes, m_conf->releaseNotesUrl() );
        setupButton( WelcomePage::Button::Donate, m_conf->donateUrl() );
    }

    //language icon
    auto icon = Calamares::Branding::instance()->image( m_conf->languageIcon(), QSize( 48, 48 ) );
    if ( !icon.isNull() )
    {
        setLanguageIcon( icon );
    }
}

void
WelcomePage::initLanguages()
{
    // Fill the list of translations
    ui->languageWidget->clear();
    ui->languageWidget->setInsertPolicy( QComboBox::InsertAtBottom );

    ui->languageWidget->setModel( m_conf->languagesModel() );
    ui->languageWidget->setItemDelegate( new LocaleTwoColumnDelegate( ui->languageWidget ) );

    ui->languageWidget->setCurrentIndex( m_conf->localeIndex() );

    connect( ui->languageWidget,
             static_cast< void ( QComboBox::* )( int ) >( &QComboBox::currentIndexChanged ),
             m_conf,
             &Config::setLocaleIndex );
}

void
WelcomePage::setupButton( Button role, const QString& url )
{
    QPushButton* button = nullptr;
    Calamares::ImageType icon = Calamares::Information;

    switch ( role )
    {
    case Button::Donate:
        button = ui->donateButton;
        icon = Calamares::Donate;
        break;
    case Button::KnownIssues:
        button = ui->knownIssuesButton;
        icon = Calamares::Bugs;
        break;
    case Button::ReleaseNotes:
        button = ui->releaseNotesButton;
        icon = Calamares::Release;
        break;
    case Button::Support:
        button = ui->supportButton;
        icon = Calamares::Help;
        break;
    }
    if ( !button )
    {
        cWarning() << "Unknown button role" << smash( role );
        return;
    }

    if ( url.isEmpty() )
    {
        button->hide();
        return;
    }

    QUrl u( url );
    if ( u.isValid() )
    {
        auto size = 2 * QSize( Calamares::defaultFontHeight(), Calamares::defaultFontHeight() );
        button->setIcon( Calamares::defaultPixmap( icon, Calamares::Original, size ) );
        connect( button, &QPushButton::clicked, [ u ]() { QDesktopServices::openUrl( u ); } );
    }
    else
    {
        cWarning() << "Welcome button" << smash( role ) << "URL" << url << "is invalid.";
        button->hide();
    }
}

void
WelcomePage::focusInEvent( QFocusEvent* e )
{
    if ( ui->languageWidget )
    {
        ui->languageWidget->setFocus();
    }
    e->accept();
}

bool
WelcomePage::verdict() const
{
    // The greeting page never blocks; the system-check page that follows does.
    return m_corryPage == QStringLiteral( "greeting" ) || m_checkingWidget->verdict();
}

void
WelcomePage::externallySelectedLanguage( int row )
{
    if ( ( row >= 0 ) && ( row < ui->languageWidget->count() ) )
    {
        ui->languageWidget->setCurrentIndex( row );
    }
}

void
WelcomePage::setLanguageIcon( QPixmap i )
{
    ui->languageIcon->setPixmap( i );
}

void
WelcomePage::retranslate()
{
    const QString message = m_conf->genericWelcomeMessage();

    if ( m_corryPage == QStringLiteral( "check" ) )
    {
        ui->mainText->setText( tr( "Is this computer ready?" ) );
    }
    else if ( !m_corryPage.isEmpty() )
    {
        ui->mainText->setText( tr( "Welcome to\n%1" ).arg( Calamares::Branding::instance()->shortProductName() ) );
    }
    else
    {
        ui->mainText->setText( message.arg( Calamares::Branding::instance()->versionedName() ) );
    }
    ui->retranslateUi( this );
    ui->supportButton->setText(
        tr( "%1 Support", "@action" ).arg( Calamares::Branding::instance()->shortProductName() ) );
}

void
LocaleTwoColumnDelegate::paint( QPainter* painter, const QStyleOptionViewItem& option, const QModelIndex& index ) const
{
    QStyledItemDelegate::paint( painter, option, index );
    option.widget->style()->drawItemText(
        painter,
        option.rect,
        Qt::AlignRight | Qt::AlignVCenter,
        option.palette,
        false,
        index.data( Calamares::Locale::TranslationsModel::EnglishLabelRole ).toString() );
}
