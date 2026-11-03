/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: configuration and compatibility rules of the "Init
 *   system" and "Boot loader" pages.
 */
#include "Config.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "network/Manager.h"
#include "utils/Logger.h"
#include "utils/Variant.h"

#include <QCoreApplication>
#include <QFile>
#include <QRegularExpression>
#include <QSysInfo>

#include <algorithm>

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

QString
debianBase( const QString& debianVersion )
{
    const QString version = debianVersion.trimmed();
    // Testing and unstable say "forky/sid"; a release says "13.1".
    if ( version.contains( QStringLiteral( "/sid" ) ) || version == QStringLiteral( "sid" ) )
    {
        return QStringLiteral( "testing" );
    }
    if ( QRegularExpression( QStringLiteral( "^[0-9]+(\\.[0-9]+)*$" ) ).match( version ).hasMatch() )
    {
        return QStringLiteral( "stable" );
    }
    return QString();
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
    if ( gs )
    {
        // The partition page publishes its planned layout when it is left
        // (corryPlannedPartitions); "partitions" itself is only written when
        // the installation runs.
        QString root, boot;
        bool rootEncrypted = false, bootEncrypted = false;
        auto partitions = gs->value( QStringLiteral( "corryPlannedPartitions" ) ).toList();
        if ( partitions.isEmpty() )
        {
            partitions = gs->value( QStringLiteral( "partitions" ) ).toList();
        }
        for ( const auto& item : partitions )
        {
            const auto partition = item.toMap();
            const auto mountPoint = partition.value( QStringLiteral( "mountPoint" ) ).toString();
            const auto fs = partition.value( QStringLiteral( "fs" ) ).toString().toLower();
            const bool encrypted = partition.value( QStringLiteral( "encrypted" ) ).toBool()
                || partition.contains( QStringLiteral( "luksMapperName" ) );
            if ( mountPoint == QStringLiteral( "/" ) )
            {
                root = fs;
                rootEncrypted = encrypted;
            }
            else if ( mountPoint == QStringLiteral( "/boot" ) )
            {
                boot = fs;
                bootEncrypted = encrypted;
            }
        }
        environment.bootFilesystem = boot.isEmpty() ? root : boot;
        // Corry's Btrfs layout mounts with zstd compression (mount.conf).
        environment.bootCompressed = environment.bootFilesystem == QStringLiteral( "btrfs" );
        environment.bootEncrypted = boot.isEmpty() ? rootEncrypted : bootEncrypted;
        // os-prober's findings from the partition page: other systems on this computer.
        environment.otherSystems = !gs->value( QStringLiteral( "osproberLines" ) ).toStringList().isEmpty();
        // The init page (before the boot loader page) wrote its choice.
        const auto init = gs->value( QStringLiteral( "corrySystem" ) ).toMap().value( QStringLiteral( "init" ) ).toMap();
        if ( !init.isEmpty() )
        {
            environment.systemdInit = init.value( QStringLiteral( "default" ), true ).toBool();
        }
    }
    return environment;
}

Config::Config( QObject* parent )
    : QObject( parent )
{
}

QString
Config::sectionKey() const
{
    return m_section == Section::Init ? QStringLiteral( "init" ) : QStringLiteral( "bootloader" );
}

QList< Option >
Config::readOptions( const QVariantList& list, const QString& base )
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
        option.availableOn = Calamares::getStringList( map, "availableOn" );
        option.isDefault = Calamares::getBool( map, "default", false );
        option.secureBoot = Calamares::getBool( map, "secureBoot", option.isDefault );
        option.needsSystemd = Calamares::getBool( map, "needsSystemd", false );
        if ( option.id.isEmpty() )
        {
            cWarning() << "corrysystem: option without id skipped";
            continue;
        }
        // Only what this Debian base's archive really has. Without a known
        // base, alternatives limited to some bases are not offered at all.
        if ( !option.isDefault && !option.availableOn.isEmpty() && !option.availableOn.contains( base ) )
        {
            cDebug() << "corrysystem: option" << option.id << "is not available on Debian" << base;
            continue;
        }
        options.append( option );
    }
    // The first option is the default unless one is marked.
    if ( !options.isEmpty()
         && std::none_of( options.cbegin(), options.cend(), []( const Option& o ) { return o.isDefault; } ) )
    {
        options.first().isDefault = true;
        options.first().secureBoot = true;
    }
    return options;
}

void
Config::setConfigurationMap( const QVariantMap& configurationMap )
{
    const QString section = Calamares::getString( configurationMap, "section" );
    m_section = section == QStringLiteral( "bootloader" )
            || ( section.isEmpty() && !configurationMap.contains( QStringLiteral( "init" ) ) )
        ? Section::BootLoader
        : Section::Init;
    m_base = Calamares::getString( configurationMap, "base" );
    if ( m_base.isEmpty() )
    {
        QFile version( QStringLiteral( "/etc/debian_version" ) );
        if ( version.open( QIODevice::ReadOnly ) )
        {
            m_base = debianBase( QString::fromUtf8( version.readAll() ) );
        }
    }
    m_options = readOptions( configurationMap.value( sectionKey() ).toList(), m_base );
    m_selected.clear();
    for ( const auto& option : std::as_const( m_options ) )
    {
        if ( option.isDefault )
        {
            m_selected = option.id;
        }
    }
    emit changed();
}

void
Config::evaluateInit( Option& option, const Environment& environment )
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
    if ( environment.gnome )
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
    if ( option.isDefault )
    {
        option.badges.prepend( QCoreApplication::translate( "Corry", "Default" ) );
        option.badges << QCoreApplication::translate( "Corry", "Works offline" );
        if ( option.secureBoot )
        {
            option.badges << QCoreApplication::translate( "Corry", "Secure Boot" );
        }
        return;
    }
    option.badges << QCoreApplication::translate( "Corry", "Needs internet" );
    if ( option.needsSystemd )
    {
        option.badges << QCoreApplication::translate( "Corry", "Needs systemd" );
    }
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
            "Corry", "Secure Boot is on. Only GRUB is installed signed; turn Secure Boot off in the firmware settings to use this loader." );
        return;
    }
    if ( option.needsSystemd && !environment.systemdInit )
    {
        // Debian's systemd-boot package depends on systemd, which elogind replaces.
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "Needs the systemd init system. Go back and choose systemd to use this loader." );
        return;
    }
    if ( environment.bootEncrypted
         && ( option.id == QStringLiteral( "extlinux" ) || option.id == QStringLiteral( "refind" ) ) )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "Cannot read an encrypted /boot. Use GRUB, or add a separate unencrypted /boot." );
        return;
    }
    if ( option.id == QStringLiteral( "extlinux" ) && environment.otherSystems )
    {
        option.available = false;
        option.reason = QCoreApplication::translate(
            "Corry", "Another operating system is on this computer. EXTLINUX would replace its boot code; GRUB keeps both bootable." );
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
    ++m_evaluation;
    for ( auto& option : m_options )
    {
        if ( m_section == Section::Init )
        {
            evaluateInit( option, environment );
        }
        else
        {
            evaluateBootLoader( option, environment );
        }
    }
    // A choice that became impossible (went offline, changed the partitions or
    // the init system) falls back to the default.
    const Option* current = option( m_selected );
    if ( !current || !current->available )
    {
        for ( const auto& o : std::as_const( m_options ) )
        {
            if ( o.isDefault )
            {
                m_selected = o.id;
            }
        }
    }
    emit changed();
}

const Option*
Config::option( const QString& id ) const
{
    for ( const auto& o : m_options )
    {
        if ( o.id == id )
        {
            return &o;
        }
    }
    return nullptr;
}

bool
Config::select( const QString& id )
{
    const auto* o = option( id );
    if ( !o || !o->available )
    {
        return false;
    }
    if ( m_selected != id )
    {
        m_selected = id;
        emit changed();
    }
    return true;
}

QVariantMap
Config::mergeInto( QVariantMap system ) const
{
    if ( const auto* o = option( m_selected ) )
    {
        system.insert( sectionKey(),
                       QVariantMap { { QStringLiteral( "id" ), o->id },
                                     { QStringLiteral( "name" ), o->name },
                                     { QStringLiteral( "packages" ), o->packages },
                                     { QStringLiteral( "default" ), o->isDefault },
                                     { QStringLiteral( "filesystems" ), o->filesystems } } );
    }
    system.insert( QStringLiteral( "online" ), m_environment.online );
    system.insert( QStringLiteral( "base" ), m_base );
    return system;
}

QString
Config::prettyStatus() const
{
    const auto* o = option( m_selected );
    if ( !o )
    {
        return QString();
    }
    const QString what = m_section == Section::Init ? QCoreApplication::translate( "Corry", "Init system" )
                                                    : QCoreApplication::translate( "Corry", "Boot loader" );
    return o->isDefault
        ? QCoreApplication::translate( "Corry", "%1: %2 (default)" ).arg( what, o->name )
        : QCoreApplication::translate( "Corry", "%1: %2 (downloaded during installation; the default is removed)" )
              .arg( what, o->name );
}

}  // namespace CorrySystem
