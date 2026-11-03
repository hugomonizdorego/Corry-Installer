/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: tests for the installation log in /tmp/Corry.
 */
#include "utils/CorryLog.h"

#include "utils/Logger.h"

#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QtTest/QtTest>

class CorryLogTests : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void testSavesReportAndSessionLog();
    void testNeverFollowsLinks();
};

void
CorryLogTests::testSavesReportAndSessionLog()
{
    QTemporaryDir temp;
    QVERIFY( temp.isValid() );
    const QString directory = temp.filePath( QStringLiteral( "Corry" ) );
    qputenv( "CORRY_LOG_DIR", QFile::encodeName( directory ) );
    // The session log of this test lives in the temporary folder too.
    qputenv( "XDG_CACHE_HOME", QFile::encodeName( temp.filePath( QStringLiteral( "cache" ) ) ) );
    QStandardPaths::setTestModeEnabled( false );
    QDir().mkpath( QStandardPaths::writableLocation( QStandardPaths::CacheLocation ) );
    Logger::setupLogLevel( Logger::LOGVERBOSE );
    Logger::setupLogfile();
    cWarning() << "Corry log test line";

    QVERIFY( Corry::lastSavedLog().isEmpty() );
    const QString path = Corry::saveInstallLog(
        QStringLiteral( "failed" ), QStringLiteral( "Boot loader files are missing" ), QStringLiteral( "no grub-pc" ) );
    QCOMPARE( path, directory + QStringLiteral( "/install.log" ) );
    QCOMPARE( Corry::lastSavedLog(), path );
    QFile file( path );
    QVERIFY( file.open( QIODevice::ReadOnly ) );
    const QString text = QString::fromUtf8( file.readAll() );
    QVERIFY( text.startsWith( QStringLiteral( "Corry Installer " ) ) );
    QVERIFY( text.contains( QStringLiteral( "Result: installation failed" ) ) );
    QVERIFY( text.contains( QStringLiteral( "Error: Boot loader files are missing" ) ) );
    QVERIFY( text.contains( QStringLiteral( "no grub-pc" ) ) );
    QVERIFY( text.contains( QStringLiteral( "----- session log -----" ) ) );
    QVERIFY( text.contains( QStringLiteral( "Corry log test line" ) ) );
    // Private to its owner: the log may hold details of the computer.
    QCOMPARE( QFileInfo( path ).permissions() & ( QFile::ReadOther | QFile::WriteOther ), QFile::Permissions() );
    // A dated copy stays next to it.
    const auto copies = QDir( directory ).entryList( { QStringLiteral( "install-*-failed.log" ) } );
    QCOMPARE( copies.count(), 1 );
}

void
CorryLogTests::testNeverFollowsLinks()
{
    QTemporaryDir temp;
    const QString victim = temp.filePath( QStringLiteral( "victim" ) );
    {
        QFile file( victim );
        QVERIFY( file.open( QIODevice::WriteOnly ) );
        file.write( "keep me\n" );
    }
    // A planted link where the log goes is replaced, never written through.
    const QString directory = temp.filePath( QStringLiteral( "Corry" ) );
    QVERIFY( QDir().mkpath( directory ) );
    QVERIFY( QFile::link( victim, directory + QStringLiteral( "/install.log" ) ) );
    qputenv( "CORRY_LOG_DIR", QFile::encodeName( directory ) );
    QVERIFY( !Corry::saveInstallLog( QStringLiteral( "finished" ), QString(), QString() ).isEmpty() );
    QVERIFY( !QFileInfo( directory + QStringLiteral( "/install.log" ) ).isSymLink() );
    QFile file( victim );
    QVERIFY( file.open( QIODevice::ReadOnly ) );
    QCOMPARE( file.readAll(), QByteArray( "keep me\n" ) );

    // The folder itself as a link: moved aside, a real folder is made.
    const QString linked = temp.filePath( QStringLiteral( "Linked" ) );
    QVERIFY( QFile::link( temp.path(), linked ) );
    qputenv( "CORRY_LOG_DIR", QFile::encodeName( linked ) );
    QVERIFY( !Corry::saveInstallLog( QStringLiteral( "finished" ), QString(), QString() ).isEmpty() );
    QVERIFY( QFileInfo( linked ).isDir() && !QFileInfo( linked ).isSymLink() );
    qunsetenv( "CORRY_LOG_DIR" );
}

QTEST_GUILESS_MAIN( CorryLogTests )

#include "utils/moc-warnings.h"

#include "TestCorryLog.moc"
