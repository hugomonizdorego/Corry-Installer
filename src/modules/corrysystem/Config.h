/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: configuration and compatibility rules of the
 *   "System components" page (init system and boot loader).
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

/// One selectable option, as listed in corrysystem.conf.
struct Option
{
    QString id;
    QString name;
    QString description;
    QStringList packages;  ///< Debian packages installed into the target.
    QStringList firmware;  ///< "bios", "efi"; empty means both.
    QStringList architectures;  ///< Debian architecture names; empty means any.
    QStringList filesystems;  ///< Allowed /boot filesystems; empty means any.
    bool isDefault = false;
    bool secureBoot = true;  ///< Usable while UEFI Secure Boot is on.
    bool needsSystemd = false;  ///< Boot loader that needs systemd's tools in the target.

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
};

/** @brief What this computer offers. With @p recheckNetwork, the internet
 * connection is tested again (synchronously) instead of using the last result.
 */
Environment detectEnvironment( bool recheckNetwork = false );
QString debianArchitecture( const QString& cpuArchitecture );

class PLUGINDLLEXPORT Config : public QObject
{
    Q_OBJECT
public:
    explicit Config( QObject* parent = nullptr );

    void setConfigurationMap( const QVariantMap& configurationMap );

    QList< Option > initSystems() const { return m_init; }
    QList< Option > bootLoaders() const { return m_bootLoaders; }
    QString selectedInit() const { return m_selectedInit; }
    QString selectedBootLoader() const { return m_selectedBootLoader; }
    Environment environment() const { return m_environment; }

    /// @brief Re-check every option against @p environment; keeps valid selections.
    void evaluate( const Environment& environment );

    bool selectInit( const QString& id );
    bool selectBootLoader( const QString& id );
    const Option* initSystem( const QString& id ) const;
    const Option* bootLoader( const QString& id ) const;

    /// @brief Map written to global storage ("corrySystem") for the jobs.
    QVariantMap toGlobalStorage() const;
    /// @brief One line per choice, for the summary page.
    QString prettyStatus() const;

signals:
    void changed();

private:
    static QList< Option > readOptions( const QVariantList& list );
    static void evaluateInit( Option& option, const Environment& environment, const QString& systemdId );
    static void evaluateBootLoader( Option& option, const Environment& environment );
    static QVariantMap optionMap( const Option& option );

    QList< Option > m_init;
    QList< Option > m_bootLoaders;
    QString m_selectedInit;
    QString m_selectedBootLoader;
    Environment m_environment;
};

}  // namespace CorrySystem

#endif
