/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "gui/PartitionDialogHelpers.h"
#include "GlobalStorage.h"
#include "JobQueue.h"
#include <QComboBox>
#include <QDialog>
#include <QLabel>
#include <QListWidget>
#include <QPushButton>
#include <QSpinBox>
#include <QToolButton>
#include <QVBoxLayout>
#include <QtTest/QtTest>

class CorryPartitionTests : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void roles()
    {
        if ( !Calamares::JobQueue::instance() ) { (void)new Calamares::JobQueue(); }
        auto* gs = Calamares::JobQueue::instance()->globalStorage();
        gs->insert( "efiSystemPartition", "/boot/efi" );
        gs->insert( "defaultFileSystemType", "btrfs" );
        gs->insert( "armInstall", true ); // Simulate EFI without reading any disk.
        // These tests use enum/name mappings only. Probing real filesystem
        // tools requires KPMcore's system DBus backend and is not a unit-test setup.
        QDialog dialog;
        auto* layout = new QVBoxLayout( &dialog );
        auto* mount = new QComboBox( &dialog ); mount->setEditable( true );
        auto* fs = new QComboBox( &dialog );
        for ( auto type : { FileSystem::Btrfs, FileSystem::Fat32, FileSystem::LinuxSwap } )
        { fs->addItem( FileSystem::nameForType( type ) ); }
        auto* flags = new QListWidget( &dialog );
        setFlagList( *flags, PartitionTable::Flag::Boot, PartitionTable::Flags() );
        layout->addWidget( mount ); layout->addWidget( fs ); layout->addWidget( flags );
        QSpinBox size;
        size.setRange( 1, 100000 );
        addPartitionRolePicker( layout, mount, fs, flags, { "/home" }, &size );
        auto click = [ &dialog ]( const QString& name ) {
            for ( auto* button : dialog.findChildren< QToolButton* >() )
            { if ( button->text() == name ) { button->click(); return true; } }
            return false;
        };
        QVERIFY( click( "EFI" ) );
        QCOMPARE( mount->currentText(), QStringLiteral( "/boot/efi" ) );
        QCOMPARE( FileSystem::typeForName( fs->currentText() ), FileSystem::Fat32 );
        QVERIFY( flagsFromList( *flags ).testFlag( PartitionTable::Flag::Boot ) );
        QCOMPARE( size.value(), 512 );
        QVERIFY( click( "Root /" ) );
        QCOMPARE( FileSystem::typeForName( fs->currentText() ), FileSystem::Btrfs );
        QVERIFY( !flagsFromList( *flags ).testFlag( PartitionTable::Flag::Boot ) );
        QVERIFY( click( "EFI" ) );
        QVERIFY( click( "Swap" ) );
        QVERIFY( mount->currentText().isEmpty() );
        QCOMPARE( FileSystem::typeForName( fs->currentText() ), FileSystem::LinuxSwap );
        QCOMPARE( size.value(), 4096 );
        QVERIFY( !flagsFromList( *flags ).testFlag( PartitionTable::Flag::Boot ) );
        QVERIFY( click( "Root /" ) );
        QCOMPARE( mount->currentText(), QStringLiteral( "/" ) );
        QCOMPARE( FileSystem::typeForName( fs->currentText() ), FileSystem::Btrfs );
        QCOMPARE( size.value(), 20480 );
        for ( auto* button : dialog.findChildren< QToolButton* >() )
        { if ( button->text() == "Home" ) { QVERIFY( !button->isEnabled() ); } }
        fs->setDisabled( true );
        QVERIFY( click( "EFI" ) );
        // Keeping an existing filesystem must never silently enable formatting.
        QVERIFY( !fs->isEnabled() );
        QCOMPARE( FileSystem::typeForName( fs->currentText() ), FileSystem::Btrfs );
    }
    void invalidMounts()
    {
        QLabel label;
        QPushButton save;
        QVERIFY( !validateMountPoint( nullptr, "/home", { "/home" }, "btrfs", &label, &save ) );
        QVERIFY( !save.isEnabled() );
        QVERIFY( !label.text().isEmpty() );
        QVERIFY( !validateMountPoint( nullptr, "home", {}, "btrfs", &label, &save ) );
        QVERIFY( !validateMountPoint( nullptr, "/", {}, FileSystem::nameForType( FileSystem::LinuxSwap ), &label, &save ) );
    }
};
QTEST_MAIN( CorryPartitionTests )
#include "CorryPartitionTests.moc"
