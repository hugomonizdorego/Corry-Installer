/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: the installation log in /tmp/Corry.
 */
#include "CorryLog.h"

#include "Branding.h"
#include "CalamaresVersion.h"
#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QProcess>
#include <QTemporaryFile>
#include <QStandardPaths>

#include <cstdio>
#include <pwd.h>
#include <sys/stat.h>
#include <unistd.h>

namespace
{
QString s_lastSaved;

/// The user who started Corry (sudo or pkexec); none when Corry runs as that user.
struct DesktopUser
{
    bool known = false;
    uid_t uid = 0;
    gid_t gid = 0;
    QString name;
};

DesktopUser
desktopUser()
{
    DesktopUser user;
    bool ok = false;
    uid_t uid = 0;
    for ( const char* variable : { "PKEXEC_UID", "SUDO_UID" } )
    {
        const QByteArray value = qgetenv( variable );
        if ( !value.isEmpty() )
        {
            uid = value.toUInt( &ok );
            if ( ok )
            {
                break;
            }
        }
    }
    if ( !ok || uid == 0 )
    {
        return user;
    }
    if ( const struct passwd* entry = getpwuid( uid ) )
    {
        user.known = true;
        user.uid = entry->pw_uid;
        user.gid = entry->pw_gid;
        user.name = QString::fromLocal8Bit( entry->pw_name );
    }
    return user;
}

/// Give @p path to the desktop user, with permissions @p mode.
void
handOver( const QString& path, mode_t mode )
{
    const QByteArray local = QFile::encodeName( path );
    const auto user = desktopUser();
    if ( user.known && geteuid() == 0 )
    {
        if ( ::lchown( local.constData(), user.uid, user.gid ) != 0 )
        {
            cWarning() << "Corry: could not give" << path << "to" << user.name;
        }
    }
    ::chmod( local.constData(), mode );
}

/// /tmp/Corry as a real directory (never through a symbolic link).
bool
prepareDirectory( const QString& directory )
{
    const QFileInfo info( directory );
    if ( info.isSymLink() || ( info.exists() && !info.isDir() ) )
    {
        // Something else is in the way; move it aside rather than follow it.
        const QString aside = directory + QStringLiteral( ".old-" ) + QString::number( QDateTime::currentSecsSinceEpoch() );
        if ( !QFile::rename( directory, aside ) )
        {
            cWarning() << "Corry: cannot use" << directory << "for the installation log.";
            return false;
        }
    }
    if ( !QDir().mkpath( directory ) )
    {
        cWarning() << "Corry: cannot create" << directory << "for the installation log.";
        return false;
    }
    handOver( directory, 0700 );
    return true;
}

QString
report( const QString& outcome, const QString& message, const QString& details )
{
    const auto* branding = Calamares::Branding::instance();
    const QString product = branding ? branding->string( Calamares::Branding::ProductName ) : QStringLiteral( "?" );
    QString text;
    text += QStringLiteral( "Corry Installer %1 (based on Calamares %2)\n" )
                .arg( QStringLiteral( CORRY_VERSION ), QStringLiteral( CALAMARES_VERSION ) );
    text += QStringLiteral( "Product: %1\n" ).arg( product );
    text += QStringLiteral( "Date: %1\n" ).arg( QDateTime::currentDateTime().toString( Qt::ISODate ) );
    text += QStringLiteral( "Result: installation %1\n" ).arg( outcome );
    if ( auto* queue = Calamares::JobQueue::instance() )
    {
        const auto system = queue->globalStorage()->value( QStringLiteral( "corrySystem" ) ).toMap();
        for ( const auto& section : { QStringLiteral( "init" ), QStringLiteral( "bootloader" ) } )
        {
            const auto choice = system.value( section ).toMap();
            if ( !choice.isEmpty() )
            {
                text += QStringLiteral( "%1: %2 %3\n" )
                            .arg( section,
                                  choice.value( QStringLiteral( "id" ) ).toString(),
                                  choice.value( QStringLiteral( "message" ) ).toString() );
            }
        }
    }
    if ( !message.isEmpty() )
    {
        text += QStringLiteral( "\nError: %1\n" ).arg( message );
    }
    if ( !details.isEmpty() )
    {
        text += QStringLiteral( "Details:\n%1\n" ).arg( details );
    }
    text += QStringLiteral( "\nLines with WARNING or ERROR below show what went wrong. The full session log "
                            "follows.\n\n----- session log -----\n" );
    return text;
}

bool
writeFile( const QString& path, const QByteArray& data )
{
    // A new file with a random name (created exclusively), renamed into place:
    // rename(2) replaces a planted symbolic link itself and never follows it.
    // (QSaveFile would write to the link's target.)
    QTemporaryFile file( path + QStringLiteral( ".XXXXXX" ) );
    file.setAutoRemove( true );
    if ( !file.open() || file.write( data ) != data.size() || !file.flush() )
    {
        cWarning() << "Corry: could not write" << path;
        return false;
    }
    if ( ::rename( QFile::encodeName( file.fileName() ).constData(), QFile::encodeName( path ).constData() ) != 0 )
    {
        cWarning() << "Corry: could not move the log to" << path;
        return false;
    }
    file.setAutoRemove( false );
    handOver( path, 0600 );
    return true;
}
}  // namespace

namespace Corry
{

QString
logDirectory()
{
    const QString overridden = qEnvironmentVariable( "CORRY_LOG_DIR" );
    return overridden.isEmpty() ? QStringLiteral( "/tmp/Corry" ) : overridden;
}

QString
saveInstallLog( const QString& outcome, const QString& message, const QString& details )
{
    const QString directory = logDirectory();
    if ( !prepareDirectory( directory ) )
    {
        return QString();
    }
    QByteArray data = report( outcome, message, details ).toUtf8();
    QFile session( Logger::logFile() );
    if ( session.open( QIODevice::ReadOnly ) )
    {
        data += session.readAll();
    }
    else
    {
        data += QStringLiteral( "(the session log %1 could not be read)\n" ).arg( Logger::logFile() ).toUtf8();
    }
    const QString stamp = QDateTime::currentDateTime().toString( QStringLiteral( "yyyyMMdd-HHmmss" ) );
    const QString dated = QDir( directory ).filePath( QStringLiteral( "install-%1-%2.log" ).arg( stamp, outcome ) );
    const QString latest = QDir( directory ).filePath( QStringLiteral( "install.log" ) );
    writeFile( dated, data );
    if ( !writeFile( latest, data ) )
    {
        return QString();
    }
    cDebug() << "Corry: installation log saved to" << latest;
    s_lastSaved = latest;
    return latest;
}

QString
lastSavedLog()
{
    return s_lastSaved;
}

bool
openInTextEditor( const QString& path )
{
    if ( path.isEmpty() || !QFile::exists( path ) )
    {
        return false;
    }
    // xdg-open uses the desktop's own text editor; the others are common
    // editors, for a session without a working default.
    QStringList programs { QStringLiteral( "xdg-open" ) };
    for ( const auto* editor : { "mousepad", "gnome-text-editor", "gedit", "kate", "kwrite", "pluma", "xed",
                                 "featherpad", "geany", "leafpad", "xterm" } )
    {
        programs << QString::fromLatin1( editor );
    }
    const auto user = desktopUser();
    for ( const auto& program : programs )
    {
        const QString executable = QStandardPaths::findExecutable( program );
        if ( executable.isEmpty() )
        {
            continue;
        }
        QStringList arguments;
        if ( program == QStringLiteral( "xterm" ) )
        {
            arguments << QStringLiteral( "-e" ) << QStringLiteral( "less" );
        }
        arguments << path;
        bool started = false;
        if ( user.known && geteuid() == 0 )
        {
            // As the desktop user, in their session (display and session bus).
            const QString runtime = QStringLiteral( "/run/user/%1" ).arg( user.uid );
            const struct passwd* entry = getpwuid( user.uid );
            QStringList environment;
            environment << QStringLiteral( "HOME=" )
                    + ( entry ? QString::fromLocal8Bit( entry->pw_dir ) : QStringLiteral( "/home/" ) + user.name );
            environment << QStringLiteral( "XDG_RUNTIME_DIR=" ) + runtime
                        << QStringLiteral( "DBUS_SESSION_BUS_ADDRESS=unix:path=" ) + runtime + QStringLiteral( "/bus" );
            for ( const auto* variable : { "DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY" } )
            {
                const QString value = qEnvironmentVariable( variable );
                if ( !value.isEmpty() )
                {
                    environment << QString::fromLatin1( variable ) + QLatin1Char( '=' ) + value;
                }
            }
            started = QProcess::startDetached( QStringLiteral( "runuser" ),
                                               QStringList { QStringLiteral( "-u" ), user.name, QStringLiteral( "--" ),
                                                             QStringLiteral( "env" ) }
                                                   + environment + QStringList { executable } + arguments );
        }
        else
        {
            started = QProcess::startDetached( executable, arguments );
        }
        if ( started )
        {
            cDebug() << "Corry: opened" << path << "with" << program;
            return true;
        }
    }
    cWarning() << "Corry: no text editor could open" << path;
    return false;
}

}  // namespace Corry
