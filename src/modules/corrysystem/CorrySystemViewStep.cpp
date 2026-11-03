/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: view step of the "Init system" and "Boot loader" pages.
 */
#include "CorrySystemViewStep.h"

#include "Config.h"
#include "CorrySystemPage.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"

CALAMARES_PLUGIN_FACTORY_DEFINITION( CorrySystemViewStepFactory, registerPlugin< CorrySystemViewStep >(); )

CorrySystemViewStep::CorrySystemViewStep( QObject* parent )
    : Calamares::ViewStep( parent )
    , m_config( new CorrySystem::Config( this ) )
{
    emit nextStatusChanged( true );
}

CorrySystemViewStep::~CorrySystemViewStep()
{
    if ( m_widget && m_widget->parent() == nullptr )
    {
        m_widget->deleteLater();
    }
}

QString
CorrySystemViewStep::prettyName() const
{
    return m_config->section() == CorrySystem::Config::Section::Init ? tr( "Init system", "@label" )
                                                                     : tr( "Boot loader", "@label" );
}

QString
CorrySystemViewStep::prettyStatus() const
{
    return m_config->prettyStatus();
}

QWidget*
CorrySystemViewStep::widget()
{
    if ( !m_widget )
    {
        m_widget = new CorrySystem::CorrySystemPage( m_config );
    }
    return m_widget;
}

bool
CorrySystemViewStep::isNextEnabled() const
{
    return true;
}

bool
CorrySystemViewStep::isBackEnabled() const
{
    return true;
}

bool
CorrySystemViewStep::isAtBeginning() const
{
    return true;
}

bool
CorrySystemViewStep::isAtEnd() const
{
    return true;
}

static void
storeChoice( const CorrySystem::Config* config )
{
    // Both pages write into one map; each changes only its own section.
    auto* gs = Calamares::JobQueue::instance()->globalStorage();
    const auto map = config->mergeInto( gs->value( QStringLiteral( "corrySystem" ) ).toMap() );
    gs->insert( QStringLiteral( "corrySystem" ), map );
    cDebug() << "Corry" << config->sectionKey() << "choice:" << map.value( config->sectionKey() );
}

void
CorrySystemViewStep::onActivate()
{
    // Re-check on every visit: the internet, the partitions or the init choice may have changed.
    m_config->evaluate( CorrySystem::detectEnvironment() );
}

void
CorrySystemViewStep::onLeave()
{
    storeChoice( m_config );
}

Calamares::JobList
CorrySystemViewStep::jobs() const
{
    return Calamares::JobList();
}

void
CorrySystemViewStep::setConfigurationMap( const QVariantMap& configurationMap )
{
    m_config->setConfigurationMap( configurationMap );
    // Written now as well, so the jobs see the default even if the page is never shown.
    storeChoice( m_config );
}
