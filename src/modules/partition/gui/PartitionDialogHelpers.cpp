/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014 Aurélien Gâteau <agateau@kde.org>
 *   SPDX-FileCopyrightText: 2016 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2018-2021 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "PartitionDialogHelpers.h"

#include "core/PartUtils.h"
#include "core/PartitionCoreModule.h"
#include "gui/CreatePartitionDialog.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"

#include <kpmcore/fs/filesystem.h>

#include <QComboBox>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QPushButton>
#include <QFile>
#include <QGridLayout>
#include <QProcess>
#include <QRadioButton>
#include <QSpinBox>
#include <QToolButton>
#include <QVBoxLayout>
#include <memory>

bool
legacyFilesystemAvailable( FileSystem::Type type )
{
    const auto name = FileSystem::nameForType( type ).toLower();
    if ( name != "jfs" && name != "reiserfs" && name != "reiser" )
    {
        return true;
    }
    const QString driver = name == "reiser" ? QStringLiteral( "reiserfs" ) : name;
    QFile filesystems( QStringLiteral( "/proc/filesystems" ) );
    if ( filesystems.open( QFile::ReadOnly ) )
    {
        for ( const auto& line : filesystems.readAll().split( '\n' ) )
        {
            if ( QString::fromLatin1( line ).simplified().split( ' ' ).last() == driver )
            {
                return true;
            }
        }
    }
    // A dry run checks for an available module without loading it.
    QProcess probe;
    probe.start( QStringLiteral( "modprobe" ), { "--dry-run", "--quiet", driver } );
    if ( !probe.waitForFinished( 1000 ) )
    {
        probe.kill();
        probe.waitForFinished();
        return false;
    }
    return probe.exitStatus() == QProcess::NormalExit && probe.exitCode() == 0;
}

void
addPartitionRolePicker( QVBoxLayout* layout, QComboBox* mount, QComboBox* filesystem,
                        QListWidget* flags, const QStringList& inUse, QSpinBox* newPartitionSize )
{
    auto* box = new QWidget( mount->parentWidget() );
    box->setObjectName( "corryRolePicker" );
    if ( auto* extended = mount->window()->findChild< QRadioButton* >( QStringLiteral( "extendedRadioButton" ) ) )
    {
        box->setDisabled( extended->isChecked() );
        QObject::connect( extended, &QRadioButton::toggled, box, &QWidget::setDisabled );
    }
    auto* grid = new QGridLayout( box );
    auto* title = new QLabel( QObject::tr( "What will this partition be used for?" ), box );
    title->setObjectName( "corrySectionTitle" );
    grid->addWidget( title, 0, 0, 1, 4 );
    struct Role { const char* title; QString path; FileSystem::Type requiredFS; const char* tip; };
    const QString efi = Calamares::JobQueue::instance()->globalStorage()->value( "efiSystemPartition" ).toString();
    const QList< Role > roles {
        { QT_TR_NOOP( "Root /" ), "/", FileSystem::Unknown, QT_TR_NOOP( "Required: system and applications." ) },
        { QT_TR_NOOP( "Home" ), "/home", FileSystem::Unknown, QT_TR_NOOP( "Personal files. Formatting erases existing files." ) },
        { QT_TR_NOOP( "EFI" ), efi, FileSystem::Fat32, QT_TR_NOOP( "UEFI boot files. Requires FAT32 and the boot flag. Recommended: 512 MiB." ) },
        { QT_TR_NOOP( "Boot" ), "/boot", FileSystem::Unknown, QT_TR_NOOP( "Optional: kernel files. Recommended: 1 GiB." ) },
        { QT_TR_NOOP( "Swap" ), QString(), FileSystem::LinuxSwap, QT_TR_NOOP( "Extra virtual memory; no mount point." ) },
        { QT_TR_NOOP( "Var" ), "/var", FileSystem::Unknown, QT_TR_NOOP( "Optional: logs, databases and cache." ) },
        { QT_TR_NOOP( "Tmp" ), "/tmp", FileSystem::Unknown, QT_TR_NOOP( "Optional: temporary files." ) }
    };
    int column = 0;
    // Remember only a flag added by this picker; retain pre-existing/manual flags.
    auto managedBootFlag = std::make_shared< bool >( false );
    for ( const auto& role : roles )
    {
        if ( role.requiredFS == FileSystem::Fat32 && ( !PartUtils::isEfiSystem() || efi.isEmpty() ) )
        {
            continue;
        }
        auto* button = new QToolButton( box );
        button->setText( QObject::tr( role.title ) );
        button->setToolTip( QObject::tr( role.tip ) );
        button->setAccessibleName( button->text() );
        button->setObjectName( "corryRoleButton" );
        button->setSizePolicy( QSizePolicy::Expanding, QSizePolicy::Preferred );
        button->setEnabled( role.path.isEmpty() || !inUse.contains( role.path ) );
        grid->addWidget( button, 1 + column / 4, column % 4 );
        ++column;
        QObject::connect( button, &QToolButton::clicked, box, [ = ] {
            // Do not silently enable formatting on an existing partition.
            // A conflicting filesystem is explained by the normal validator.
            FileSystem::Type desiredFS = role.requiredFS;
            if ( desiredFS == FileSystem::Unknown
                 && s_unmountableFS.contains( FileSystem::typeForName( filesystem->currentText() ) ) )
            {
                PartUtils::canonicalFilesystemName(
                    Calamares::JobQueue::instance()->globalStorage()->value( "defaultFileSystemType" ).toString(), &desiredFS );
            }
            if ( filesystem->isEnabled() && desiredFS != FileSystem::Unknown )
            {
                int index = -1;
                for ( int i = 0; i < filesystem->count(); ++i )
                {
                    if ( FileSystem::typeForName( filesystem->itemText( i ) ) == desiredFS )
                    {
                        index = i;
                        break;
                    }
                }
                if ( index < 0 )
                {
                    return;
                }
                filesystem->setCurrentIndex( index );
            }
            if ( role.requiredFS == FileSystem::LinuxSwap
                 && FileSystem::typeForName( filesystem->currentText() ) != FileSystem::LinuxSwap )
            {
                return;
            }
            setSelectedMountPoint( *mount, role.path );
            if ( newPartitionSize )
            {
                int recommended = role.requiredFS == FileSystem::Fat32 ? 512
                    : role.requiredFS == FileSystem::LinuxSwap ? 4096
                    : role.path == "/boot" ? 1024 : role.path == "/" ? 20480 : 0;
                if ( recommended )
                {
                    newPartitionSize->setValue( qBound( newPartitionSize->minimum(), recommended, newPartitionSize->maximum() ) );
                }
            }
            for ( int i = 0; i < flags->count(); ++i )
            {
                auto* flag = flags->item( i );
                if ( flag->data( Qt::UserRole ).toInt() == int( PartitionTable::Flag::Boot ) )
                {
                    if ( role.requiredFS == FileSystem::Fat32 && flag->checkState() != Qt::Checked )
                    {
                        *managedBootFlag = true;
                        flag->setCheckState( Qt::Checked );
                    }
                    else if ( role.requiredFS != FileSystem::Fat32 && *managedBootFlag )
                    {
                        flag->setCheckState( Qt::Unchecked );
                        *managedBootFlag = false;
                    }
                }
            }
        } );
    }
    auto* help = new QLabel( QObject::tr( "Choose a role, then check size and filesystem below. Changes are applied only after the final installation confirmation." ), box );
    help->setWordWrap( true );
    help->setObjectName( "corryHint" );
    grid->addWidget( help, 3, 0, 1, 4 );
    layout->insertWidget( 0, box );
}

QStringList
standardMountPoints()
{
    QStringList mountPoints { "/", "/boot", "/home", "/opt", "/srv", "/usr", "/var", "/tmp" };
    if ( PartUtils::isEfiSystem() )
    {
        mountPoints << Calamares::JobQueue::instance()->globalStorage()->value( "efiSystemPartition" ).toString();
    }
    mountPoints.removeDuplicates();
    mountPoints.sort();
    return mountPoints;
}

void
standardMountPoints( QComboBox& combo )
{
    combo.clear();
    combo.lineEdit()->setPlaceholderText( QObject::tr( "(no mount point)" ) );
    combo.addItems( standardMountPoints() );
}

void
standardMountPoints( QComboBox& combo, const QString& selected )
{
    standardMountPoints( combo );
    setSelectedMountPoint( combo, selected );
}

QString
selectedMountPoint( QComboBox& combo )
{
    return combo.currentText();
}

void
setSelectedMountPoint( QComboBox& combo, const QString& selected )
{
    if ( selected.isEmpty() )
    {
        combo.setCurrentIndex( -1 );  // (no mount point)
    }
    else
    {
        for ( int i = 0; i < combo.count(); ++i )
        {
            if ( selected == combo.itemText( i ) )
            {
                combo.setCurrentIndex( i );
                return;
            }
        }
        combo.addItem( selected );
        combo.setCurrentIndex( combo.count() - 1 );
    }
}

bool
validateMountPoint( PartitionCoreModule* core, const QString& mountPoint, const QStringList& inUse, const QString& fileSystem, QLabel* label, QPushButton* button )
{
    QString msg;
    bool ok = true;

    if ( !mountPoint.isEmpty() && inUse.contains( mountPoint ) )
    {
        msg = CreatePartitionDialog::tr( "Mountpoint already in use. Please select another one.", "@info" );
        ok = false;
    }
    else if ( !mountPoint.isEmpty() && !mountPoint.startsWith( '/' ) )
    {
        msg = CreatePartitionDialog::tr( "Mountpoint must start with a <tt>/</tt>.", "@info" );
        ok = false;
    } else {
        // Validate the chosen filesystem + mountpoint combination.
        FileSystem::Type selectedFsType;
        selectedFsType = FileSystem::typeForName( fileSystem );
        if ( selectedFsType == FileSystem::Unknown )
        {
            PartUtils::canonicalFilesystemName( fileSystem, &selectedFsType );
        }
        if ( !mountPoint.isEmpty() && s_unmountableFS.contains( selectedFsType ) )
        {
            msg = CreatePartitionDialog::tr( "This filesystem cannot have a mount point. Choose a Linux filesystem for system folders.", "@info" );
            if ( label )
            {
                label->setText( msg );
            }
            if ( button )
            {
                button->setEnabled( false );
            }
            return false;
        }
        bool fsTypeIsAllowed = false;
        if ( selectedFsType == FileSystem::Type::Unknown )
        {
            fsTypeIsAllowed = true;
        }
        else
        {
            QList< FileSystem::Type > anyAllowedFsTypes = core->dirFSRestrictLayout().anyAllowedFSTypes();
            for ( auto& anyAllowedFsType : anyAllowedFsTypes )
            {
                if ( selectedFsType == anyAllowedFsType )
                {
                    fsTypeIsAllowed = true;
                    break;
                }
            }
        }

        bool fsTypeIsAllowedForMountPoint = false;
        // We allow arbitrary unmountable filesystems here since an
        // unmountable filesystem has no mount point associated with it, thus
        // any filesystem restriction we'd find at this point would be
        // irrelevant.
        if ( selectedFsType == FileSystem::Type::Unknown || s_unmountableFS.contains( selectedFsType ) )
        {
            fsTypeIsAllowedForMountPoint = true;
        }
        else
        {
            QList< FileSystem::Type > allowedFsTypes = core->dirFSRestrictLayout().allowedFSTypes( mountPoint, inUse, false );
            for ( auto& allowedFsType : allowedFsTypes )
            {
                if ( selectedFsType == allowedFsType )
                {
                    fsTypeIsAllowedForMountPoint = true;
                    break;
                }
            }
        }

        if ( !fsTypeIsAllowed ) {
            msg = CreatePartitionDialog::tr( "Filesystem is prohibited by this distro. Consider selecting another one.", "@info" );
            ok = false;
        }
        else if ( !fsTypeIsAllowedForMountPoint ) {
            msg = CreatePartitionDialog::tr( "Filesystem is prohibited for use on this mountpoint. Consider selecting a different filesystem or mountpoint.", "@info" );
            ok = false;
        }
    }

    if ( label )
    {
        label->setText( msg );
    }
    if ( button )
    {
        button->setEnabled( ok );
    }
    return ok;
}


PartitionTable::Flags
flagsFromList( const QListWidget& list )
{
    PartitionTable::Flags flags;

    for ( int i = 0; i < list.count(); i++ )
    {
        if ( list.item( i )->checkState() == Qt::Checked )
        {
            flags |= static_cast< PartitionTable::Flag >( list.item( i )->data( Qt::UserRole ).toInt() );
        }
    }

    return flags;
}

void
setFlagList( QListWidget& list, PartitionTable::Flags available, PartitionTable::Flags checked )
{
    int f = 1;
    QString s;
    while ( !( s = PartitionTable::flagName( static_cast< PartitionTable::Flag >( f ) ) ).isEmpty() )
    {
        if ( available & f )
        {
            QListWidgetItem* item = new QListWidgetItem( s );
            list.addItem( item );
            item->setFlags( Qt::ItemIsUserCheckable | Qt::ItemIsEnabled );
            item->setData( Qt::UserRole, f );
            item->setCheckState( ( checked & f ) ? Qt::Checked : Qt::Unchecked );
        }

        f <<= 1;
    }
}
