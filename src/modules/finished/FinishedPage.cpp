/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014-2015 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2017-2018 Adriaan de Groot <groot@kde.org>
 *   SPDX-FileCopyrightText: 2019 Collabora Ltd <arnaud.ferraris@collabora.com>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "FinishedPage.h"

#include "Config.h"
#include "ui_FinishedPage.h"

#include "Branding.h"
#include "Settings.h"
#include "compat/CheckBox.h"
#include "utils/Retranslator.h"

#include <QFocusEvent>
#include <QRadioButton>
#include <QVBoxLayout>
#include <QLabel>


FinishedPage::FinishedPage( Config* config, QWidget* parent )
    : QWidget( parent )
    , ui( new Ui::FinishedPage )
    , m_config( config )
{
    ui->setupUi( this );

    ui->mainText->setAlignment( Qt::AlignCenter );
    ui->mainText->setWordWrap( true );
    ui->mainText->setOpenExternalLinks( true );

    connect( config,
             &Config::restartModeChanged,
             [ this ]( Config::RestartMode mode )
             {
                 using Mode = Config::RestartMode;

                 ui->restartCheckBox->setVisible( !m_corryOptions && mode != Mode::Never );
                 ui->restartCheckBox->setEnabled( mode != Mode::Always );
                 if ( m_corryOptions ) { m_corryOptions->setVisible( mode != Mode::Never ); }
             } );
    connect( config, &Config::restartNowWantedChanged, ui->restartCheckBox, &QCheckBox::setChecked );
    connect( ui->restartCheckBox,
             Calamares::checkBoxStateChangedSignal,
             [ config ]( Calamares::checkBoxStateType state )
             { config->setRestartNowWanted( state != Calamares::checkBoxUncheckedValue ); } );

    if ( Calamares::Branding::instance()->componentName() == QStringLiteral( "corry" ) )
    {
        ui->restartCheckBox->hide();
        m_corryOptions = new QWidget( this );
        m_corryOptions->setObjectName( "corryFinishOptions" );
        auto* choices = new QVBoxLayout( m_corryOptions );
        m_continueLive = new QRadioButton( tr( "Continue testing the live session" ), m_corryOptions );
        m_continueLive->setObjectName( "corryContinueLive" );
        m_restart = new QRadioButton( tr( "Restart into the installed system when I click Done" ), m_corryOptions );
        m_restart->setObjectName( "corryRestart" );
        m_continueLive->setChecked( true );
        choices->addWidget( m_continueLive );
        choices->addWidget( m_restart );
        ui->verticalLayout_2->insertWidget( 0, m_corryOptions );
        connect( m_restart, &QRadioButton::toggled, config, &Config::setRestartNowWanted );
        connect( config, &Config::restartNowWantedChanged, this, [ this ]( bool wanted ) {
            m_restart->setChecked( wanted ); m_continueLive->setChecked( !wanted );
        } );
    }

    CALAMARES_RETRANSLATE_SLOT( &FinishedPage::retranslate );
}

void FinishedPage::setConfigurationMap( const QVariantMap& configuration )
{
    m_corryContent = configuration;
    retranslate();
}

void
FinishedPage::focusInEvent( QFocusEvent* e )
{
    e->accept();
}

void
FinishedPage::onInstallationFailed( const QString& message, const QString& details )
{
    m_failure = !message.isEmpty() ? message : details;
    if ( m_corryOptions )
    {
        m_config->setRestartNowWanted( false );
        m_corryOptions->hide();
    }
    retranslate();
}

void
FinishedPage::retranslate()
{

    const auto* branding = Calamares::Branding::instance();

    ui->retranslateUi( this );
    if ( !m_failure.has_value() )
    {
        if ( m_corryOptions )
        {
            m_continueLive->setText( m_corryContent.value( "corryContinueLiveText", tr( "Continue testing the live session" ) ).toString() );
            m_restart->setText( m_corryContent.value( "corryRestartText", tr( "Restart into the installed system when I click Done" ) ).toString() );
        }
        if ( Calamares::Settings::instance()->isSetupMode() )
        {
            ui->mainText->setText( tr( "<h1>All done.</h1><br/>"
                                       "%1 has been set up on your computer.<br/>"
                                       "You may now start using your new system.",
                                       "@info" )
                                       .arg( branding->versionedName() ) );
            ui->restartCheckBox->setToolTip( tr( "<html><head/><body>"
                                                 "<p>When this box is checked, your system will "
                                                 "restart immediately when you click on "
                                                 "<span style=\"font-style:italic;\">Done</span> "
                                                 "or close the setup program.</p></body></html>",
                                                 "@tooltip" ) );
        }
        else
        {
            ui->mainText->setText( tr( "<h1>All done.</h1><br/>"
                                       "%1 has been installed on your computer.<br/>"
                                       "You may now restart into your new system, or continue "
                                       "using the %2 Live environment.",
                                       "@info" )
                                       .arg( branding->versionedName(), branding->productName() ) );
            ui->restartCheckBox->setToolTip( tr( "<html><head/><body>"
                                                 "<p>When this box is checked, your system will "
                                                 "restart immediately when you click on "
                                                 "<span style=\"font-style:italic;\">Done</span> "
                                                 "or close the installer.</p></body></html>",
                                                 "@tooltip" ) );
        }
        if ( m_corryOptions && m_corryContent.contains( "corryFinishedTitle" ) )
        {
            ui->mainText->setText( "<h1>" + m_corryContent.value( "corryFinishedTitle" ).toString().toHtmlEscaped()
                + "</h1><br/>" + m_corryContent.value( "corryFinishedDescription" ).toString().toHtmlEscaped() );
        }
    }
    else
    {
        const QString message = m_failure.value();

        if ( Calamares::Settings::instance()->isSetupMode() )
        {
            ui->mainText->setText( tr( "<h1>Setup Failed</h1><br/>"
                                       "%1 has not been set up on your computer.<br/>"
                                       "The error message was: %2.",
                                       "@info, %1 is product name with version" )
                                       .arg( branding->versionedName() )
                                       .arg( message ) );
        }
        else
        {
            ui->mainText->setText( tr( "<h1>Installation Failed</h1><br/>"
                                       "%1 has not been installed on your computer.<br/>"
                                       "The error message was: %2.",
                                       "@info, %1 is product name with version" )
                                       .arg( branding->versionedName() )
                                       .arg( message ) );
        }
    }
}
