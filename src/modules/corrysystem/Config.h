/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: configuration and compatibility rules of the "Init
 *   system" and "Boot loader" pages. One module, two instances: each instance
 *   is configured with a section (init or bootloader) and the Debian base.
 */
#ifndef CORRYSYSTEM_CONFIG_H
#define CORRYSYSTEM_CONFIG_H

#include "DllMacro.h"

#include <QList>
#include <QObject>
#include <QStringList>
#include <QVariantMap>

namespace CorrySystem
{

/// One selectable option, as listed in corrysystem-<section>.conf.
struct Option
{
    QString id;
    QString name;
    QString description;
    QStringList packages;  ///< Debian packages installed into the target.
    QStringList firmware;  ///< "bios", "efi"; empty means both.
    QStringList architectures;  ///< Debian architecture names; empty means any.
    QStringList filesystems;  ///< Allowed /boot filesystems; empty means any.
    QStringList availableOn;  ///< Debian bases whose archive has the packages; empty means all.
    bool isDefault = false;
    bool secureBoot = true;  ///< Usable while UEFI Secure Boot is on.
    bool needsSystemd = false;  ///< Boot loader whose Debian package needs the systemd init.

    // Filled in by Config::evaluate()
    bool available = true;
    QString reason;  ///< Why the option cannot be chosen on this computer.
    QStringList badges;  ///< Short hints shown next to the name.
};

/// What was found on this computer; detectable without a target system.
struct Environment
{
    bool online = false;
    QString firmware = QStringLiteral( "bios" );  ///< "bios" or "efi"
    QString architecture = QStringLiteral( "amd64" );  ///< Debian architecture name
    bool secureBoot = false;
    bool gnome = false;  ///< GDM/GNOME Shell present: they require systemd.
    QString bootFilesystem;  ///< Filesystem of /boot (or /); empty when unknown.
    bool bootCompressed = false;  ///< Btrfs with compression (Corry's default).
    bool bootEncrypted = false;  ///< /boot (or / without a /boot) is inside LUKS.
    bool otherSystems = false;  ///< os-prober found another operating system.
    bool systemdInit = true;  ///< The init system chosen on the init page is systemd (the default).
};

/** @brief What this computer offers. With @p recheckNetwork, the internet
 * connection is tested again (synchronously) instead of using the last result.
 */
Environment detectEnvironment( bool recheckNetwork = false );
QString debianArchitecture( const QString& cpuArchitecture );
/// @brief "stable" or "testing" from the contents of /etc/debian_version; empty if unknown.
QString debianBase( const QString& debianVersion );

class PLUGINDLLEXPORT Config : public QObject
{
    Q_OBJECT
public:
    enum class Section
    {
        Init,
        BootLoader
    };

    explicit Config( QObject* parent = nullptr );

    void setConfigurationMap( const QVariantMap& configurationMap );

    Section section() const { return m_section; }
    /// @brief The key of this section in global storage ("init" or "bootloader").
    QString sectionKey() const;
    QString base() const { return m_base; }
    QList< Option > options() const { return m_options; }
    QString selected() const { return m_selected; }
    Environment environment() const { return m_environment; }
    int evaluation() const { return m_evaluation; }

    /// @brief Re-check every option against @p environment; keeps a valid selection.
    void evaluate( const Environment& environment );

    bool select( const QString& id );
    const Option* option( const QString& id ) const;

    /// @brief @p system ("corrySystem" in global storage) with this section's choice.
    QVariantMap mergeInto( QVariantMap system ) const;
    /// @brief One line for the summary page.
    QString prettyStatus() const;

signals:
    void changed();

private:
    static QList< Option > readOptions( const QVariantList& list, const QString& base );
    static void evaluateInit( Option& option, const Environment& environment );
    static void evaluateBootLoader( Option& option, const Environment& environment );

    Section m_section = Section::Init;
    QString m_base;
    QList< Option > m_options;
    QString m_selected;
    Environment m_environment;
    int m_evaluation = 0;
};

}  // namespace CorrySystem

#endif
