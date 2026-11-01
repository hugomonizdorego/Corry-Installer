/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: view step of the "System components" page.
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
    return tr( "System", "@label" );
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

void
CorrySystemViewStep::onActivate()
{
    // Re-check on every visit: the internet or the partitions may have changed.
    m_config->setProperty( "evaluation", m_config->property( "evaluation" ).toInt() + 1 );
    m_config->evaluate( CorrySystem::detectEnvironment() );
}

void
CorrySystemViewStep::onLeave()
{
    const auto map = m_config->toGlobalStorage();
    Calamares::JobQueue::instance()->globalStorage()->insert( QStringLiteral( "corrySystem" ), map );
    cDebug() << "Corry system components:" << map;
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
    // Written now as well, so the jobs see the defaults even if the page is never shown.
    Calamares::JobQueue::instance()->globalStorage()->insert( QStringLiteral( "corrySystem" ),
                                                               m_config->toGlobalStorage() );
}
