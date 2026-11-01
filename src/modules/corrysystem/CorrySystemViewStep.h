/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: view step of the "System components" page.
 */
#ifndef CORRYSYSTEMVIEWSTEP_H
#define CORRYSYSTEMVIEWSTEP_H

#include "DllMacro.h"
#include "utils/PluginFactory.h"
#include "viewpages/ViewStep.h"

namespace CorrySystem
{
class Config;
class CorrySystemPage;
}  // namespace CorrySystem

class PLUGINDLLEXPORT CorrySystemViewStep : public Calamares::ViewStep
{
    Q_OBJECT
public:
    explicit CorrySystemViewStep( QObject* parent = nullptr );
    ~CorrySystemViewStep() override;

    QString prettyName() const override;
    QString prettyStatus() const override;
    QWidget* widget() override;

    bool isNextEnabled() const override;
    bool isBackEnabled() const override;
    bool isAtBeginning() const override;
    bool isAtEnd() const override;

    void onActivate() override;
    void onLeave() override;

    Calamares::JobList jobs() const override;
    void setConfigurationMap( const QVariantMap& configurationMap ) override;

private:
    CorrySystem::Config* m_config;
    CorrySystem::CorrySystemPage* m_widget = nullptr;
};

CALAMARES_PLUGIN_FACTORY_DECLARATION( CorrySystemViewStepFactory )

#endif
