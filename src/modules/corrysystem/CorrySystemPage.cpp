/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: the "System components" page.
 */
#include "CorrySystemPage.h"

#include "utils/Retranslator.h"

#include <QGridLayout>
#include <QHBoxLayout>
#include <QKeyEvent>
#include <QLabel>
#include <QMouseEvent>
#include <QPushButton>
#include <QRadioButton>
#include <QScrollArea>
#include <QStyle>
#include <QVBoxLayout>

namespace CorrySystem
{

static QLabel*
badge( const QString& text, const char* objectName, QWidget* parent )
{
    auto* label = new QLabel( text, parent );
    label->setObjectName( QString::fromLatin1( objectName ) );
    return label;
}

OptionCard::OptionCard( const Option& option, QWidget* parent )
    : QFrame( parent )
    , m_id( option.id )
    , m_radio( new QRadioButton( this ) )
{
    setObjectName( QStringLiteral( "corryOption" ) );
    setProperty( "selected", false );
    setCursor( option.available ? Qt::PointingHandCursor : Qt::ForbiddenCursor );
    setFocusPolicy( option.available ? Qt::StrongFocus : Qt::NoFocus );
    setAccessibleName( option.name );
    setEnabled( option.available );
    m_radio->setFocusPolicy( Qt::NoFocus );
    m_radio->setAutoExclusive( false );
    m_radio->setAccessibleName( option.name );

    auto* row = new QHBoxLayout( this );
    row->setContentsMargins( 14, 10, 14, 10 );
    row->setSpacing( 12 );
    row->addWidget( m_radio, 0, Qt::AlignTop );
    auto* column = new QVBoxLayout;
    column->setSpacing( 3 );
    row->addLayout( column, 1 );

    auto* head = new QHBoxLayout;
    head->setSpacing( 6 );
    auto* title = new QLabel( option.name, this );
    title->setObjectName( QStringLiteral( "corryOptionTitle" ) );
    head->addWidget( title );
    for ( const auto& text : option.badges )
    {
        const bool warning = text.contains( QStringLiteral( "internet" ), Qt::CaseInsensitive );
        const bool muted = text == tr( "Works offline" ) || text == tr( "UEFI only" ) || text == tr( "BIOS only" )
            || text == tr( "ARM" );
        head->addWidget(
            badge( text, warning ? "corryBadgeWarning" : muted ? "corryBadgeMuted" : "corryBadge", this ) );
    }
    head->addStretch();
    column->addLayout( head );

    auto* text = new QLabel( option.description, this );
    text->setObjectName( QStringLiteral( "corryOptionText" ) );
    text->setWordWrap( true );
    column->addWidget( text );
    if ( !option.reason.isEmpty() )
    {
        auto* reason = new QLabel( option.reason, this );
        reason->setObjectName( QStringLiteral( "corryOptionReason" ) );
        reason->setWordWrap( true );
        column->addWidget( reason );
    }
    connect( m_radio, &QRadioButton::clicked, this, [ this ] { emit chosen( m_id ); } );
}

void
OptionCard::setSelected( bool selected )
{
    m_radio->setChecked( selected );
    setProperty( "selected", selected );
    style()->unpolish( this );
    style()->polish( this );
    update();
}

void
OptionCard::mousePressEvent( QMouseEvent* event )
{
    if ( isEnabled() && event->button() == Qt::LeftButton )
    {
        emit chosen( m_id );
    }
    QFrame::mousePressEvent( event );
}

void
OptionCard::keyPressEvent( QKeyEvent* event )
{
    if ( event->key() == Qt::Key_Space || event->key() == Qt::Key_Return || event->key() == Qt::Key_Enter )
    {
        emit chosen( m_id );
        return;
    }
    QFrame::keyPressEvent( event );
}

CorrySystemPage::CorrySystemPage( Config* config, QWidget* parent )
    : QWidget( parent )
    , m_config( config )
{
    auto* layout = new QVBoxLayout( this );
    layout->setContentsMargins( 0, 0, 0, 0 );
    layout->setSpacing( 10 );
    auto* statusRow = new QHBoxLayout;
    statusRow->setSpacing( 12 );
    m_status = new QLabel( this );
    m_status->setObjectName( QStringLiteral( "corryHint" ) );
    m_status->setWordWrap( true );
    statusRow->addWidget( m_status, 1 );
    auto* recheck = new QPushButton( this );
    recheck->setObjectName( QStringLiteral( "corryRecheckButton" ) );
    CALAMARES_RETRANSLATE( recheck->setText( tr( "Check again" ) );
                           recheck->setToolTip( tr( "Test the internet connection again and refresh the options." ) ); );
    connect( recheck,
             &QPushButton::clicked,
             this,
             [ this ]
             {
                 m_config->setProperty( "evaluation", m_config->property( "evaluation" ).toInt() + 1 );
                 m_config->evaluate( detectEnvironment( true ) );
             } );
    statusRow->addWidget( recheck, 0, Qt::AlignTop );
    layout->addLayout( statusRow );
    auto* scroll = new QScrollArea( this );
    scroll->setWidgetResizable( true );
    scroll->setFrameShape( QFrame::NoFrame );
    scroll->setHorizontalScrollBarPolicy( Qt::ScrollBarAlwaysOff );
    layout->addWidget( scroll, 1 );
    m_content = new QWidget( scroll );
    m_contentLayout = new QVBoxLayout( m_content );
    m_contentLayout->setContentsMargins( 0, 0, 6, 0 );
    m_contentLayout->setSpacing( 10 );
    scroll->setWidget( m_content );
    connect( m_config, &Config::changed, this, &CorrySystemPage::rebuild );
    rebuild();
}

void
CorrySystemPage::addSection( QVBoxLayout* into, const QString& title, const QString& text,
                             const QList< Option >& options, const QString& selected, bool isInit )
{
    auto* heading = new QLabel( title, m_content );
    heading->setObjectName( QStringLiteral( "corrySectionTitle" ) );
    into->addWidget( heading );
    auto* hint = new QLabel( text, m_content );
    hint->setObjectName( QStringLiteral( "corryHint" ) );
    hint->setWordWrap( true );
    into->addWidget( hint );
    auto* grid = new QGridLayout;
    grid->setHorizontalSpacing( 12 );
    grid->setVerticalSpacing( 10 );
    int index = 0;
    for ( const auto& option : options )
    {
        auto* card = new OptionCard( option, m_content );
        card->setSelected( option.id == selected );
        connect( card,
                 &OptionCard::chosen,
                 this,
                 [ this, isInit ]( const QString& id )
                 {
                     if ( isInit )
                     {
                         m_config->selectInit( id );
                     }
                     else
                     {
                         m_config->selectBootLoader( id );
                     }
                 } );
        grid->addWidget( card, index / 2, index % 2 );
        ( isInit ? m_initCards : m_bootCards ).append( card );
        ++index;
    }
    grid->setColumnStretch( 0, 1 );
    grid->setColumnStretch( 1, 1 );
    into->addLayout( grid );
}

void
CorrySystemPage::rebuild()
{
    // Selection changes only re-tick the cards; a new evaluation rebuilds them.
    const bool sameCards = m_initCards.size() == m_config->initSystems().size()
        && m_bootCards.size() == m_config->bootLoaders().size() && !m_initCards.isEmpty()
        && property( "corryEvaluation" ).toInt() == m_config->property( "evaluation" ).toInt();
    if ( sameCards )
    {
        for ( auto* card : m_initCards )
        {
            card->setSelected( card->id() == m_config->selectedInit() );
        }
        for ( auto* card : m_bootCards )
        {
            card->setSelected( card->id() == m_config->selectedBootLoader() );
        }
        return;
    }
    setProperty( "corryEvaluation", m_config->property( "evaluation" ) );
    m_initCards.clear();
    m_bootCards.clear();
    while ( auto* item = m_contentLayout->takeAt( 0 ) )
    {
        if ( auto* widget = item->widget() )
        {
            widget->deleteLater();
        }
        else if ( auto* nested = item->layout() )
        {
            while ( auto* inner = nested->takeAt( 0 ) )
            {
                if ( auto* widget = inner->widget() )
                {
                    widget->deleteLater();
                }
                delete inner;
            }
        }
        delete item;
    }
    const auto environment = m_config->environment();
    m_status->setText( environment.online
                           ? tr( "<b>Online.</b> Every option can be downloaded. Computer: %1, %2%3." )
                                 .arg( environment.firmware == QStringLiteral( "efi" ) ? tr( "UEFI" ) : tr( "BIOS" ),
                                       environment.architecture,
                                       environment.secureBoot ? tr( ", Secure Boot on" ) : QString() )
                           : tr( "<b>Offline.</b> Only the defaults can be installed. Connect to the internet, "
                                 "then press Check again to enable the alternatives." ) );
    addSection( m_contentLayout,
                tr( "Init system" ),
                tr( "The first program the kernel starts; it brings up services and the desktop." ),
                m_config->initSystems(),
                m_config->selectedInit(),
                true );
    m_contentLayout->addSpacing( 6 );
    addSection( m_contentLayout,
                tr( "Boot loader" ),
                tr( "The program the firmware starts first; it loads the kernel. When an alternative is chosen, "
                    "GRUB is removed from the new system after the alternative has been installed and checked. "
                    "If that fails, GRUB is installed instead." ),
                m_config->bootLoaders(),
                m_config->selectedBootLoader(),
                false );
    m_contentLayout->addStretch( 1 );
}

}  // namespace CorrySystem
