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
#include <QLabel>
#include <QIcon>
#include <QFile>


FinishedPage::FinishedPage( Config* config, QWidget* parent )
    : QWidget( parent )
    , ui( new Ui::FinishedPage )
{
    ui->setupUi( this );

    ui->mainText->setAlignment( Qt::AlignCenter );
    ui->mainText->setWordWrap( true );
    ui->mainText->setOpenExternalLinks( true );

    const auto* branding = Calamares::Branding::instance();
    if ( branding->componentName() == QStringLiteral( "corry" ) )
    {
        // Corry: the "ready" illustration above the message.
        const QString image = branding->componentDirectory() + QStringLiteral( "/slides/ready.svg" );
        if ( QFile::exists( image ) )
        {
            auto* picture = new QLabel( this );
            picture->setAlignment( Qt::AlignCenter );
            picture->setPixmap( QIcon( image ).pixmap( QSize( 400, 225 ) ) );
            ui->verticalLayout->insertWidget( ui->verticalLayout->indexOf( ui->mainText ), picture );
        }
        ui->mainText->setObjectName( "corryFinishedText" );
    }

    connect( config,
             &Config::restartModeChanged,
             [ this ]( Config::RestartMode mode )
             {
                 using Mode = Config::RestartMode;

                 ui->restartCheckBox->setVisible( mode != Mode::Never );
                 ui->restartCheckBox->setEnabled( mode != Mode::Always );
             } );
    connect( config, &Config::restartNowWantedChanged, ui->restartCheckBox, &QCheckBox::setChecked );
    connect( ui->restartCheckBox,
             Calamares::checkBoxStateChangedSignal,
             [ config ]( Calamares::checkBoxStateType state )
             { config->setRestartNowWanted( state != Calamares::checkBoxUncheckedValue ); } );

    CALAMARES_RETRANSLATE_SLOT( &FinishedPage::retranslate );
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
    retranslate();
}

void
FinishedPage::retranslate()
{

    const auto* branding = Calamares::Branding::instance();

    ui->retranslateUi( this );
    if ( !m_failure.has_value() )
    {
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
        else if ( branding->componentName() == QStringLiteral( "corry" ) )
        {
            ui->mainText->setText( tr( "<h1>%1 is installed.</h1>"
                                       "<p>Corry has removed itself from the new system. Restart the computer, "
                                       "remove the installation media when asked, and sign in with your new account.</p>"
                                       "<p>You can also keep using the live session.</p>" )
                                       .arg( branding->shortProductName() ) );
            ui->restartCheckBox->setToolTip( tr( "Restart when you press Done." ) );
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
        else if ( branding->componentName() == QStringLiteral( "corry" ) )
        {
            ui->mainText->setText( tr( "<h1>The installation stopped</h1>"
                                       "<p>%1 could not be installed: %2.</p>"
                                       "<p>Press <i>Show details</i> on the previous page for the full log, check the "
                                       "disk and the installation media, then try again.</p>" )
                                       .arg( branding->shortProductName() )
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
