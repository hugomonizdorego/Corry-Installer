/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: configuration and compatibility rules of the
 *   "System components" page.
 */
#include "Config.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "network/Manager.h"
#include "utils/Logger.h"
#include "utils/Variant.h"

#include <QCoreApplication>
#include <QFile>
#include <QSysInfo>

namespace CorrySystem
{

QString
debianArchitecture( const QString& cpuArchitecture )
{
    static const QMap< QString, QString > names {
        { QStringLiteral( "x86_64" ), QStringLiteral( "amd64" ) },
        { QStringLiteral( "i386" ), QStringLiteral( "i386" ) },
        { QStringLiteral( "arm64" ), QStringLiteral( "arm64" ) },
        { QStringLiteral( "arm" ), QStringLiteral( "armhf" ) },
        { QStringLiteral( "riscv64" ), QStringLiteral( "riscv64" ) },
        { QStringLiteral( "loongarch64" ), QStringLiteral( "loong64" ) },
        { QStringLiteral( "power64" ), QStringLiteral( "ppc64el" ) },
    };
    return names.value( cpuArchitecture, cpuArchitecture );
}

static bool
secureBootEnabled()
{
    // Byte 4 of the SecureBoot variable is 1 when Secure Boot is enforced.
    QFile variable( QStringLiteral( "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c" ) );
    if ( !variable.open( QIODevice::ReadOnly ) )
    {
        return false;
    }
    const QByteArray data = variable.read( 5 );
    return data.size() == 5 && data.at( 4 ) == 1;
}

Environment
detectEnvironment( bool recheckNetwork )
{
    Environment environment;
    auto* gs = Calamares::JobQueue::instance() ? Calamares::JobQueue::instance()->globalStorage() : nullptr;
    // The manager is a thin handle on one shared state (see network/Manager.h).
    Calamares::Network::Manager network;
    environment.online = recheckNetwork ? network.checkHasInternet() : network.hasInternet();
    if ( !recheckNetwork && gs && gs->contains( QStringLiteral( "hasInternet" ) ) )
    {
        environment.online = environment.online || gs->value( QStringLiteral( "hasInternet" ) ).toBool();
    }
    if ( recheckNetwork && gs )
    {
        gs->insert( QStringLiteral( "hasInternet" ), environment.online );
    }
    environment.firmware = QFile::exists( QStringLiteral( "/sys/firmware/efi" ) ) ? QStringLiteral( "efi" )
                                                                                   : QStringLiteral( "bios" );
    if ( gs && gs->contains( QStringLiteral( "firmwareType" ) ) )
    {
        environment.firmware = gs->value( QStringLiteral( "firmwareType" ) ).toString();
    }
    environment.architecture = debianArchitecture( QSysInfo::currentCpuArchitecture() );
    environment.secureBoot = environment.firmware == QStringLiteral( "efi" ) && secureBootEnabled();
    environment.gnome
        = QFile::exists( QStringLiteral( "/usr/sbin/gdm3" ) ) || QFile::exists( QStringLiteral( "/usr/bin/gnome-shell" ) );
    // The partition page (before this one) describes the planned layout.
    if ( gs )
    {
        QString root, boot;
        bool rootCompressed = false;
        const auto partitions = gs->value( QStringLiteral( "partitions" ) ).toList();
        for ( const auto& item : partitions )
        {
            const auto partition = item.toMap();
            const auto mountPoint = partition.value( QStringLiteral( "mountPoint" ) ).toString();
            const auto fs = partition.value( QStringLiteral( "fs" ) ).toString().toLower();
            if ( mountPoint == QStringLiteral( "/" ) )
            {
                root = fs;
                // Corry's Btrfs layout mounts with zstd compression (fstab.conf).
                rootCompressed = fs == QStringLiteral( "btrfs" );
            }
            else if ( mountPoint == QStringLiteral( "/boot" ) )
            {
                boot = fs;
            }
        }
        environment.bootFilesystem = boot.isEmpty() ? root : boot;
        environment.bootCompressed = boot.isEmpty() && rootCompressed;
    }
    return environment;
}

Config::Config( QObject* parent )
    : QObject( parent )
{
}

QList< Option >
Config::readOptions( const QVariantList& list )
{
    QList< Option > options;
    for ( const auto& item : list )
    {
        const auto map = item.toMap();
        Option option;
        option.id = Calamares::getString( map, "id" );
        option.name = Calamares::getString( map, "name", option.id );
        option.description = Calamares::getString( map, "description" );
        option.packages = Calamares::getStringList( map, "packages" );
        option.firmware = Calamares::getStringList( map, "firmware" );
        option.architectures = Calamares::getStringList( map, "architectures" );
        option.filesystems = Calamares::getStringList( map, "filesystems" );
        option.isDefault = Calamares::getBool( map, "default", false );
        option.secureBoot = Calamares::getBool( map, "secureBoot", option.isDefault );
        option.needsSystemd = Calamares::getBool( map, "needsSystemd", false );
        if ( option.id.isEmpty() )
        {
            cWarning() << "corrysystem: option without id skipped";
            continue;
        }
        options.append( option );
    }
    return options;
}

void
Config::setConfigurationMap( const QVariantMap& configurationMap )
{
    m_init = readOptions( configurationMap.value( QStringLiteral( "init" ) ).toList() );
    m_bootLoaders = readOptions( configurationMap.value( QStringLiteral( "bootloader" ) ).toList() );
    // The first option is the default unless one is marked.
    auto markDefault = []( QList< Option >& options )
    {
        if ( options.isEmpty() )
        {
            return;
        }
        if ( std::none_of( options.cbegin(), options.cend(), []( const Option& o ) { return o.isDefault; } ) )
        {
            options.first().isDefault = true;
            options.first().secureBoot = true;
        }
    };
    markDefault( m_init );
    markDefault( m_bootLoaders );
    for ( const auto& option : m_init )
    {
        if ( option.isDefault )
        {
            m_selectedInit = option.id;
        }
    }
    for ( const auto& option : m_bootLoaders )
    {
        if ( option.isDefault )
        {
            m_selectedBootLoader = option.id;
        }
    }
    emit changed();
}

void
Config::evaluateInit( Option& option, const Environment& environment, const QString& systemdId )
{
    option.available = true;
    option.reason.clear();
    option.badges.clear();
    if ( option.isDefault )
    {
        option.badges << QCoreApplication::translate( "Corry", "Default" )
                      << QCoreApplication::translate( "Corry", "Works offline" );
        return;
    }
    option.badges << QCoreApplication::translate( "Corry", "Needs internet" );
    if ( !option.architectures.isEmpty() && !option.architectures.contains( environment.architecture ) )
    {
        option.available = false;
        option.reason = QCoreApplication::translate( "Corry", "Not available for %1 computers." )
                            .arg( environment.architecture );
        return;
    }
    if ( environment.gnome && option.id != systemdId )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "This live image uses GNOME (GDM), which needs systemd. Not available on this image." );
        return;
    }
    if ( !environment.online )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "Connect to the internet to download it; the computer is offline." );
    }
}

void
Config::evaluateBootLoader( Option& option, const Environment& environment )
{
    option.available = true;
    option.reason.clear();
    option.badges.clear();
    const bool efi = environment.firmware == QStringLiteral( "efi" );
    if ( option.firmware.size() == 1 )
    {
        option.badges << ( option.firmware.first() == QStringLiteral( "efi" )
                               ? QCoreApplication::translate( "Corry", "UEFI only" )
                               : QCoreApplication::translate( "Corry", "BIOS only" ) );
    }
    if ( !option.architectures.isEmpty() )
    {
        option.badges << ( option.architectures.contains( QStringLiteral( "arm64" ) )
                               ? QCoreApplication::translate( "Corry", "ARM" )
                               : option.architectures.join( QStringLiteral( ", " ) ) );
    }
    if ( option.isDefault )
    {
        option.badges.prepend( QCoreApplication::translate( "Corry", "Default" ) );
        option.badges << QCoreApplication::translate( "Corry", "Works offline" );
        return;
    }
    option.badges << QCoreApplication::translate( "Corry", "Needs internet" );
    if ( !option.architectures.isEmpty() && !option.architectures.contains( environment.architecture ) )
    {
        option.available = false;
        option.reason = QCoreApplication::translate( "Corry", "Only for %1 computers; this one is %2." )
                            .arg( option.architectures.join( QStringLiteral( "/" ) ), environment.architecture );
        return;
    }
    if ( !option.firmware.isEmpty() && !option.firmware.contains( environment.firmware ) )
    {
        option.available = false;
        option.reason = efi ? QCoreApplication::translate( "Corry", "This computer starts with UEFI; this loader is for BIOS." )
                            : QCoreApplication::translate( "Corry", "This computer starts in BIOS mode; this loader needs UEFI." );
        return;
    }
    if ( environment.secureBoot && !option.secureBoot )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "Secure Boot is on. Debian signs only GRUB; turn Secure Boot off in the firmware settings to use this loader." );
        return;
    }
    if ( option.id == QStringLiteral( "extlinux" ) && environment.bootCompressed )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "EXTLINUX cannot read Corry's compressed Btrfs. Choose ext4 for /, or add a separate ext4 /boot." );
        return;
    }
    if ( !option.filesystems.isEmpty() && !environment.bootFilesystem.isEmpty()
         && !option.filesystems.contains( environment.bootFilesystem ) )
    {
        option.available = false;
        option.reason = QCoreApplication::translate( "Corry", "Cannot read a %1 /boot. Use %2 for / or a separate /boot." )
                            .arg( environment.bootFilesystem, option.filesystems.join( QStringLiteral( ", " ) ) );
        return;
    }
    if ( !environment.online )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "Connect to the internet to download it; the computer is offline." );
    }
}

void
Config::evaluate( const Environment& environment )
{
    m_environment = environment;
    QString systemdId;
    for ( const auto& option : m_init )
    {
        if ( option.isDefault )
        {
            systemdId = option.id;
        }
    }
    for ( auto& option : m_init )
    {
        evaluateInit( option, environment, systemdId );
    }
    for ( auto& option : m_bootLoaders )
    {
        evaluateBootLoader( option, environment );
        if ( option.needsSystemd )
        {
            option.badges << QCoreApplication::translate( "Corry", "Needs systemd" );
            // Debian's systemd-boot package depends on systemd, which elogind replaces.
            if ( option.available && !m_selectedInit.isEmpty() && m_selectedInit != systemdId )
            {
                option.available = false;
                option.reason = QCoreApplication::translate(
                    "Corry", "Needs the systemd init system; choose systemd above to use this loader." );
            }
        }
    }
    // A choice that became impossible (went offline, changed the partitions) falls back to the default.
    auto fallback = []( const QList< Option >& options, QString& selected )
    {
        const Option* current = nullptr;
        for ( const auto& option : options )
        {
            if ( option.id == selected )
            {
                current = &option;
            }
        }
        if ( !current || !current->available )
        {
            for ( const auto& option : options )
            {
                if ( option.isDefault )
                {
                    selected = option.id;
                }
            }
        }
    };
    fallback( m_init, m_selectedInit );
    fallback( m_bootLoaders, m_selectedBootLoader );
    emit changed();
}

const Option*
Config::initSystem( const QString& id ) const
{
    for ( const auto& option : m_init )
    {
        if ( option.id == id )
        {
            return &option;
        }
    }
    return nullptr;
}

const Option*
Config::bootLoader( const QString& id ) const
{
    for ( const auto& option : m_bootLoaders )
    {
        if ( option.id == id )
        {
            return &option;
        }
    }
    return nullptr;
}

bool
Config::selectInit( const QString& id )
{
    const auto* option = initSystem( id );
    if ( !option || !option->available )
    {
        return false;
    }
    if ( m_selectedInit == id )
    {
        return true;
    }
    m_selectedInit = id;
    // Boot loaders that need systemd follow the init choice.
    const bool affectsLoaders = std::any_of(
        m_bootLoaders.cbegin(), m_bootLoaders.cend(), []( const Option& o ) { return o.needsSystemd; } );
    if ( affectsLoaders )
    {
        setProperty( "evaluation", property( "evaluation" ).toInt() + 1 );
        evaluate( m_environment );
        return true;
    }
    emit changed();
    return true;
}

bool
Config::selectBootLoader( const QString& id )
{
    const auto* option = bootLoader( id );
    if ( !option || !option->available )
    {
        return false;
    }
    m_selectedBootLoader = id;
    emit changed();
    return true;
}

QVariantMap
Config::optionMap( const Option& option )
{
    return { { QStringLiteral( "id" ), option.id },
             { QStringLiteral( "name" ), option.name },
             { QStringLiteral( "packages" ), option.packages },
             { QStringLiteral( "default" ), option.isDefault } };
}

QVariantMap
Config::toGlobalStorage() const
{
    QVariantMap map;
    if ( const auto* init = initSystem( m_selectedInit ) )
    {
        map.insert( QStringLiteral( "init" ), optionMap( *init ) );
    }
    if ( const auto* loader = bootLoader( m_selectedBootLoader ) )
    {
        map.insert( QStringLiteral( "bootloader" ), optionMap( *loader ) );
    }
    map.insert( QStringLiteral( "online" ), m_environment.online );
    return map;
}

QString
Config::prettyStatus() const
{
    auto describe = []( const Option* option )
    {
        if ( !option )
        {
            return QCoreApplication::translate( "Corry", "unchanged" );
        }
        return option->isDefault ? QCoreApplication::translate( "Corry", "%1 (default)" ).arg( option->name )
                                 : QCoreApplication::translate( "Corry", "%1 (downloaded during installation; "
                                                                         "the default is removed)" )
                                       .arg( option->name );
    };
    return QCoreApplication::translate( "Corry", "Init system: %1<br/>Boot loader: %2" )
        .arg( describe( initSystem( m_selectedInit ) ), describe( bootLoader( m_selectedBootLoader ) ) );
}

}  // namespace CorrySystem
