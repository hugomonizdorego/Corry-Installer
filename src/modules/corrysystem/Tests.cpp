/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: compatibility rules of the "Init system" and "Boot
 *   loader" pages.
 */
#include "Config.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"
#include "utils/Yaml.h"

#include <QtTest/QtTest>

using namespace CorrySystem;

class CorrySystemTests : public QObject
{
    Q_OBJECT
public:
    CorrySystemTests() {}
    ~CorrySystemTests() override {}

private Q_SLOTS:
    void initTestCase();
    void testBaseDetection();
    void testSectionsAndAvailability();
    void testOfflineKeepsDefaults();
    void testFirmwareSecureBootAndFilesystems();
    void testBootLoaderFollowsTheInitChoice();
    void testGnomeBlocksOtherInits();
    void testGlobalStorageAndSummary();

private:
    QVariantMap configuration( const char* section, const QString& base );
};

QVariantMap
CorrySystemTests::configuration( const char* section, const QString& base )
{
    // The shipped configuration, so the tests follow what users see.
    const auto path = QString::fromLatin1( BUILD_AS_TEST ) + QStringLiteral( "/corrysystem-%1.conf" ).arg( section );
    bool ok = false;
    auto map = Calamares::YAML::load( path, &ok );
    if ( !ok )
    {
        cWarning() << "Could not load" << path;
    }
    map.insert( QStringLiteral( "base" ), base );
    return map;
}

void
CorrySystemTests::initTestCase()
{
    Logger::setupLogLevel( Logger::LOGDEBUG );
    (void)new Calamares::JobQueue();
}

void
CorrySystemTests::testBaseDetection()
{
    QCOMPARE( debianBase( QStringLiteral( "13.1\n" ) ), QStringLiteral( "stable" ) );
    QCOMPARE( debianBase( QStringLiteral( "13" ) ), QStringLiteral( "stable" ) );
    QCOMPARE( debianBase( QStringLiteral( "forky/sid\n" ) ), QStringLiteral( "testing" ) );
    QCOMPARE( debianBase( QStringLiteral( "bookworm/sid" ) ), QStringLiteral( "testing" ) );
    QCOMPARE( debianBase( QStringLiteral( "something" ) ), QString() );
    QCOMPARE( debianArchitecture( QStringLiteral( "x86_64" ) ), QStringLiteral( "amd64" ) );
}

void
CorrySystemTests::testSectionsAndAvailability()
{
    Config init;
    init.setConfigurationMap( configuration( "init", QStringLiteral( "stable" ) ) );
    QCOMPARE( init.section(), Config::Section::Init );
    QCOMPARE( init.sectionKey(), QStringLiteral( "init" ) );
    QCOMPARE( init.options().size(), 4 );
    QCOMPARE( init.selected(), QStringLiteral( "systemd" ) );
    QVERIFY( init.option( QStringLiteral( "systemd" ) )->isDefault );
    QVERIFY( init.option( QStringLiteral( "systemd" ) )->packages.isEmpty() );

    // Debian stable has rEFInd; Debian testing does not. U-Boot is never offered (amd64).
    Config stable;
    stable.setConfigurationMap( configuration( "bootloader", QStringLiteral( "stable" ) ) );
    QCOMPARE( stable.section(), Config::Section::BootLoader );
    QCOMPARE( stable.options().size(), 4 );
    QVERIFY( stable.option( QStringLiteral( "refind" ) ) );
    QVERIFY( !stable.option( QStringLiteral( "uboot" ) ) );
    QCOMPARE( stable.selected(), QStringLiteral( "grub" ) );

    Config testing;
    testing.setConfigurationMap( configuration( "bootloader", QStringLiteral( "testing" ) ) );
    QCOMPARE( testing.options().size(), 3 );
    QVERIFY( !testing.option( QStringLiteral( "refind" ) ) );
    QVERIFY( testing.option( QStringLiteral( "systemd-boot" ) ) );
    QVERIFY( testing.option( QStringLiteral( "extlinux" ) ) );

    // An unknown base offers only the defaults and options without a base limit.
    Config unknown;
    auto map = configuration( "bootloader", QStringLiteral( "" ) );
    map.insert( QStringLiteral( "base" ), QStringLiteral( "nonsense" ) );
    unknown.setConfigurationMap( map );
    QCOMPARE( unknown.options().size(), 1 );
    QCOMPARE( unknown.selected(), QStringLiteral( "grub" ) );
}

void
CorrySystemTests::testOfflineKeepsDefaults()
{
    Config init;
    init.setConfigurationMap( configuration( "init", QStringLiteral( "stable" ) ) );
    Environment offline;
    offline.online = false;
    offline.firmware = QStringLiteral( "efi" );
    init.evaluate( offline );
    for ( const auto& option : init.options() )
    {
        QCOMPARE( option.available, option.isDefault );
        if ( !option.isDefault )
        {
            QVERIFY( option.reason.contains( QStringLiteral( "offline" ) ) );
        }
    }
    QVERIFY( !init.select( QStringLiteral( "runit" ) ) );
    QCOMPARE( init.selected(), QStringLiteral( "systemd" ) );

    // Chosen online, then the connection drops: back to the default.
    Environment online = offline;
    online.online = true;
    init.evaluate( online );
    QVERIFY( init.select( QStringLiteral( "runit" ) ) );
    init.evaluate( offline );
    QCOMPARE( init.selected(), QStringLiteral( "systemd" ) );

    Config loader;
    loader.setConfigurationMap( configuration( "bootloader", QStringLiteral( "stable" ) ) );
    loader.evaluate( online );
    QVERIFY( loader.select( QStringLiteral( "refind" ) ) );
    loader.evaluate( offline );
    QCOMPARE( loader.selected(), QStringLiteral( "grub" ) );
}

void
CorrySystemTests::testFirmwareSecureBootAndFilesystems()
{
    Config config;
    config.setConfigurationMap( configuration( "bootloader", QStringLiteral( "stable" ) ) );
    Environment bios;
    bios.online = true;
    bios.firmware = QStringLiteral( "bios" );
    bios.bootFilesystem = QStringLiteral( "ext4" );
    config.evaluate( bios );
    QVERIFY( config.option( QStringLiteral( "grub" ) )->available );
    QVERIFY( config.option( QStringLiteral( "extlinux" ) )->available );
    QVERIFY( !config.option( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( !config.option( QStringLiteral( "refind" ) )->available );

    // Corry's default Btrfs with compression is not readable by EXTLINUX.
    Environment btrfs = bios;
    btrfs.bootFilesystem = QStringLiteral( "btrfs" );
    btrfs.bootCompressed = true;
    config.evaluate( btrfs );
    QVERIFY( !config.option( QStringLiteral( "extlinux" ) )->available );
    QVERIFY( config.option( QStringLiteral( "extlinux" ) )->reason.contains( QStringLiteral( "Btrfs" ) ) );

    Environment efi = bios;
    efi.firmware = QStringLiteral( "efi" );
    config.evaluate( efi );
    QVERIFY( config.option( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( config.option( QStringLiteral( "refind" ) )->available );
    QVERIFY( !config.option( QStringLiteral( "extlinux" ) )->available );

    // rEFInd reads ext2/3/4 and Btrfs, but has no XFS driver.
    Environment xfs = efi;
    xfs.bootFilesystem = QStringLiteral( "xfs" );
    config.evaluate( xfs );
    QVERIFY( !config.option( QStringLiteral( "refind" ) )->available );
    QVERIFY( config.option( QStringLiteral( "systemd-boot" ) )->available );  // kernels on the ESP

    // 32-bit UEFI (tablets): GRUB only.
    Environment efi32 = efi;
    efi32.efi32 = true;
    config.evaluate( efi32 );
    QVERIFY( config.option( QStringLiteral( "grub" ) )->available );
    QVERIFY( !config.option( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( config.option( QStringLiteral( "systemd-boot" ) )->reason.contains( QStringLiteral( "32-bit" ) ) );

    // Neither rEFInd nor EXTLINUX can read LUKS; systemd-boot keeps kernels on the ESP.
    Environment encrypted = efi;
    encrypted.bootEncrypted = true;
    config.evaluate( encrypted );
    QVERIFY( !config.option( QStringLiteral( "refind" ) )->available );
    QVERIFY( config.option( QStringLiteral( "refind" ) )->reason.contains( QStringLiteral( "encrypted" ) ) );
    QVERIFY( config.option( QStringLiteral( "systemd-boot" ) )->available );

    // EXTLINUX would overwrite another system's boot code.
    Environment dualBoot = bios;
    dualBoot.otherSystems = true;
    config.evaluate( dualBoot );
    QVERIFY( !config.option( QStringLiteral( "extlinux" ) )->available );
    QVERIFY( config.option( QStringLiteral( "grub" ) )->available );

    Environment secure = efi;
    secure.secureBoot = true;
    config.evaluate( secure );
    QVERIFY( config.option( QStringLiteral( "grub" ) )->available );
    for ( const auto& id : { QStringLiteral( "systemd-boot" ), QStringLiteral( "refind" ) } )
    {
        QVERIFY2( !config.option( id )->available, qPrintable( id ) );
        QVERIFY2( config.option( id )->reason.contains( QStringLiteral( "Secure Boot" ) ), qPrintable( id ) );
    }
}

void
CorrySystemTests::testBootLoaderFollowsTheInitChoice()
{
    // Debian's systemd-boot package depends on systemd, which elogind replaces.
    Config config;
    config.setConfigurationMap( configuration( "bootloader", QStringLiteral( "testing" ) ) );
    Environment efi;
    efi.online = true;
    efi.firmware = QStringLiteral( "efi" );
    efi.bootFilesystem = QStringLiteral( "ext4" );
    config.evaluate( efi );
    QVERIFY( config.select( QStringLiteral( "systemd-boot" ) ) );
    Environment runit = efi;
    runit.systemdInit = false;
    config.evaluate( runit );
    QVERIFY( !config.option( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( config.option( QStringLiteral( "systemd-boot" ) )->reason.contains( QStringLiteral( "systemd" ) ) );
    QCOMPARE( config.selected(), QStringLiteral( "grub" ) );

    // The init page's choice reaches the boot loader page through global storage.
    auto* gs = Calamares::JobQueue::instance()->globalStorage();
    gs->insert( QStringLiteral( "corrySystem" ),
                QVariantMap { { QStringLiteral( "init" ),
                                QVariantMap { { QStringLiteral( "id" ), QStringLiteral( "openrc" ) },
                                              { QStringLiteral( "default" ), false } } } } );
    QVERIFY( !detectEnvironment().systemdInit );
    gs->remove( QStringLiteral( "corrySystem" ) );
    QVERIFY( detectEnvironment().systemdInit );

    // The partition page's planned layout (published when it is left) is what
    // the page checks; "partitions" only exists once the installation runs.
    QVERIFY( detectEnvironment().bootFilesystem.isEmpty() );
    gs->insert( QStringLiteral( "corryPlannedPartitions" ),
                QVariantList { QVariantMap { { QStringLiteral( "mountPoint" ), QStringLiteral( "/" ) },
                                             { QStringLiteral( "fs" ), QStringLiteral( "btrfs" ) },
                                             { QStringLiteral( "encrypted" ), true } } } );
    auto planned = detectEnvironment();
    QCOMPARE( planned.bootFilesystem, QStringLiteral( "btrfs" ) );
    QVERIFY( planned.bootCompressed );
    QVERIFY( planned.bootEncrypted );
    gs->insert( QStringLiteral( "corryPlannedPartitions" ),
                QVariantList { QVariantMap { { QStringLiteral( "mountPoint" ), QStringLiteral( "/" ) },
                                             { QStringLiteral( "fs" ), QStringLiteral( "btrfs" ) },
                                             { QStringLiteral( "encrypted" ), true } },
                               QVariantMap { { QStringLiteral( "mountPoint" ), QStringLiteral( "/boot" ) },
                                             { QStringLiteral( "fs" ), QStringLiteral( "ext4" ) } } } );
    gs->insert( QStringLiteral( "osproberLines" ), QStringList { QStringLiteral( "/dev/sda1:Windows 10:Windows:chain" ) } );
    planned = detectEnvironment();
    QCOMPARE( planned.bootFilesystem, QStringLiteral( "ext4" ) );
    QVERIFY( !planned.bootCompressed );
    QVERIFY( !planned.bootEncrypted );
    QVERIFY( planned.otherSystems );
    gs->remove( QStringLiteral( "corryPlannedPartitions" ) );
    gs->remove( QStringLiteral( "osproberLines" ) );
}

void
CorrySystemTests::testGnomeBlocksOtherInits()
{
    Config config;
    config.setConfigurationMap( configuration( "init", QStringLiteral( "testing" ) ) );
    Environment gnome;
    gnome.online = true;
    gnome.gnome = true;
    config.evaluate( gnome );
    QVERIFY( config.option( QStringLiteral( "systemd" ) )->available );
    for ( const auto& option : config.options() )
    {
        if ( !option.isDefault )
        {
            QVERIFY( !option.available );
            QVERIFY( option.reason.contains( QStringLiteral( "GNOME" ) ) );
        }
    }
    QVERIFY( !config.select( QStringLiteral( "openrc" ) ) );
}

void
CorrySystemTests::testGlobalStorageAndSummary()
{
    Environment online;
    online.online = true;
    online.firmware = QStringLiteral( "efi" );
    online.bootFilesystem = QStringLiteral( "ext4" );

    Config init;
    init.setConfigurationMap( configuration( "init", QStringLiteral( "stable" ) ) );
    init.evaluate( online );
    QVERIFY( init.select( QStringLiteral( "sysvinit" ) ) );
    Config loader;
    loader.setConfigurationMap( configuration( "bootloader", QStringLiteral( "stable" ) ) );
    loader.evaluate( online );
    QVERIFY( loader.select( QStringLiteral( "refind" ) ) );

    // Each page changes only its own section of the shared map.
    QVariantMap system = loader.mergeInto( init.mergeInto( QVariantMap() ) );
    const auto initChoice = system.value( QStringLiteral( "init" ) ).toMap();
    QCOMPARE( initChoice.value( QStringLiteral( "id" ) ).toString(), QStringLiteral( "sysvinit" ) );
    QVERIFY( !initChoice.value( QStringLiteral( "default" ) ).toBool() );
    QVERIFY( initChoice.value( QStringLiteral( "packages" ) ).toStringList().contains( QStringLiteral( "elogind" ) ) );
    const auto loaderChoice = system.value( QStringLiteral( "bootloader" ) ).toMap();
    QCOMPARE( loaderChoice.value( QStringLiteral( "id" ) ).toString(), QStringLiteral( "refind" ) );
    QVERIFY( loaderChoice.value( QStringLiteral( "packages" ) ).toStringList().contains( QStringLiteral( "refind" ) ) );
    QCOMPARE( system.value( QStringLiteral( "base" ) ).toString(), QStringLiteral( "stable" ) );
    QVERIFY( system.value( QStringLiteral( "online" ) ).toBool() );
    // Going back and choosing again replaces only that section.
    QVERIFY( init.select( QStringLiteral( "systemd" ) ) );
    system = init.mergeInto( system );
    QCOMPARE( system.value( QStringLiteral( "init" ) ).toMap().value( QStringLiteral( "id" ) ).toString(),
              QStringLiteral( "systemd" ) );
    QCOMPARE( system.value( QStringLiteral( "bootloader" ) ).toMap().value( QStringLiteral( "id" ) ).toString(),
              QStringLiteral( "refind" ) );

    QVERIFY( init.prettyStatus().contains( QStringLiteral( "systemd (default)" ) ) );
    QVERIFY( loader.prettyStatus().contains( QStringLiteral( "rEFInd" ) ) );
    QVERIFY( loader.prettyStatus().contains( QStringLiteral( "removed" ) ) );
}

QTEST_GUILESS_MAIN( CorrySystemTests )

#include "utils/moc-warnings.h"

#include "Tests.moc"
