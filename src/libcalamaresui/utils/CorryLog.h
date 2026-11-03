/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: the installation log in /tmp/Corry.
 *
 *   When the installation fails (and also when it finishes), the whole
 *   session log is saved to /tmp/Corry/install.log, with a dated copy next
 *   to it. The files belong to the desktop user (the one who started Corry),
 *   so they can be opened, copied and edited in any text editor.
 */
#ifndef CORRY_LOG_H
#define CORRY_LOG_H

#include "DllMacro.h"

#include <QString>

namespace Corry
{

/// The folder of the saved logs: /tmp/Corry (CORRY_LOG_DIR overrides it, for tests).
UIDLLEXPORT QString logDirectory();

/** @brief Save the session log with a short report on top.
 *
 * @p outcome is "failed" or "finished". Returns the path of
 * /tmp/Corry/install.log, or an empty string when nothing could be written.
 */
UIDLLEXPORT QString saveInstallLog( const QString& outcome, const QString& message, const QString& details );

/// The path returned by the last successful saveInstallLog(); empty before.
UIDLLEXPORT QString lastSavedLog();

/// Open @p path in a text editor, as the desktop user when Corry runs as root.
UIDLLEXPORT bool openInTextEditor( const QString& path );

}  // namespace Corry

#endif
