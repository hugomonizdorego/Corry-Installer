// SPDX-License-Identifier: GPL-3.0-or-later
#include "Config.h"
#include <QFile>
#include <QTemporaryDir>
#include <QtTest>

class CorryFinishedTests : public QObject
{
    Q_OBJECT
private slots:
    void rebootIsExplicitAndDisabledAfterFailure()
    {
        QTemporaryDir temp;
        QVERIFY( temp.isValid() );
        const QString marker = temp.filePath( "restart-requested" );
        Config config;
        config.setConfigurationMap( { { "restartNowMode", "user-unchecked" },
            { "restartNowCommand", QString( "touch '%1'" ).arg( marker ) } } );
        QVERIFY( !config.restartNowWanted() );
        config.doRestart(); // The live session remains running by default.
        QVERIFY( !QFile::exists( marker ) );
        config.setRestartNowWanted( true );
        QVERIFY( config.restartNowWanted() );
        QVERIFY( !QFile::exists( marker ) ); // Choosing the radio button does not execute anything.
        config.setRestartNowWanted( false );
        config.doRestart();
        QVERIFY( !QFile::exists( marker ) );
        config.setRestartNowWanted( true );
        config.doRestart(); // Test fixture command only, never an actual reboot.
        QVERIFY( QFile::remove( marker ) );
        config.onInstallationFailed( "Fixture failure", "Details" );
        config.setRestartNowWanted( true );
        QVERIFY( !config.restartNowWanted() );
        config.doRestart( true );
        QVERIFY( !QFile::exists( marker ) );
    }
};
QTEST_GUILESS_MAIN( CorryFinishedTests )
#include "CorryFinishedTests.moc"
