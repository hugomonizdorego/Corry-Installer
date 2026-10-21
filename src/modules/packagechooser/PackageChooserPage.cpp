/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2019 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "PackageChooserPage.h"

#include "ui_page_package.h"

#include "utils/Gui.h"
#include "utils/Logger.h"
#include "utils/Retranslator.h"

#include <QLabel>
#include <QBoxLayout>
#include <QProcess>
#include <QPushButton>
#include <QTimer>

PackageChooserPage::PackageChooserPage( PackageChooserMode mode, QWidget* parent )
    : QWidget( parent )
    , ui( new Ui::PackageChooserPage )
    , m_introduction( QString(),
                      QString(),
                      tr( "Package Selection" ),
                      tr( "Please pick a product from the list. The selected product will be installed." ) )
{
    m_introduction.screenshot = QPixmap( QStringLiteral( ":/images/no-selection.png" ) );

    ui->setupUi( this );
    CALAMARES_RETRANSLATE( updateLabels(); );

    switch ( mode )
    {
    case PackageChooserMode::Optional:
        [[fallthrough]];
    case PackageChooserMode::Required:
        ui->products->setSelectionMode( QAbstractItemView::SingleSelection );
        break;
    case PackageChooserMode::OptionalMultiple:
        [[fallthrough]];
    case PackageChooserMode::RequiredMultiple:
        ui->products->setSelectionMode( QAbstractItemView::ExtendedSelection );
    }

    ui->products->setMinimumWidth( 10 * Calamares::defaultFontHeight() );
}

void
PackageChooserPage::enableCorryRepositoryCheck()
{
    if ( m_corryCheck )
    {
        return;
    }
    m_corryCheck = true;
    ui->products->setSelectionMode( QAbstractItemView::MultiSelection );
    auto* panel = new QWidget( this );
    auto* row = new QHBoxLayout( panel );
    auto* status = new QLabel( tr( "Checking internet and signed repositories…" ), panel );
    status->setWordWrap( true );
    status->setTextFormat( Qt::PlainText );
    auto* retry = new QPushButton( tr( "Check again" ), panel );
    row->addWidget( status, 1 );
    row->addWidget( retry );
    qobject_cast< QBoxLayout* >( layout() )->insertWidget( 0, panel );
    auto* process = new QProcess( this );
    auto* timeout = new QTimer( process );
    timeout->setSingleShot( true );
    timeout->setInterval( 115000 );
    connect( timeout, &QTimer::timeout, process, &QProcess::kill );
    connect( retry, &QPushButton::clicked, this, [ = ]() {
        if ( process->state() != QProcess::NotRunning )
        {
            return;
        }
        m_repositoriesReady = false;
        emit selectionChanged();
        retry->setEnabled( false );
        status->setText( tr( "Checking internet and signed repositories…" ) );
        process->start( QStringLiteral( "/usr/bin/python3" ),
                        { QStringLiteral( "/usr/lib/corry/repository-check.py" ) } );
        timeout->start();
    } );
    connect( process, QOverload< int, QProcess::ExitStatus >::of( &QProcess::finished ), this,
             [ = ]( int code, QProcess::ExitStatus state ) {
        timeout->stop();
        m_repositoriesReady = code == 0 && state == QProcess::NormalExit;
        status->setText( m_repositoriesReady
            ? tr( "Signed repositories are reachable. Packages will be downloaded before partitioning." )
            : tr( "Repositories are unavailable. Check your connection, system date and repository settings, then retry. Deselect additional software to continue offline." ) );
        retry->setEnabled( true );
        emit selectionChanged();
    } );
    connect( process, &QProcess::errorOccurred, this, [ = ]( QProcess::ProcessError ) {
        timeout->stop();
        m_repositoriesReady = false;
        retry->setEnabled( true );
        status->setText( tr( "Repository check failed. Retry or deselect additional software to continue offline." ) );
        emit selectionChanged();
    } );
    QTimer::singleShot( 0, retry, &QPushButton::click );
}

void
PackageChooserPage::currentChanged( const QModelIndex& index )
{
    if ( !index.isValid() || !ui->products->selectionModel()->hasSelection() )
    {
        ui->productName->setText( m_introduction.name.get() );
        ui->productScreenshot->setPixmap( m_introduction.screenshot );
        ui->productDescription->setText( m_introduction.description.get() );
    }
    else
    {
        const auto* model = ui->products->model();

        ui->productName->setText( model->data( index, PackageListModel::NameRole ).toString() );
        ui->productDescription->setText( model->data( index, PackageListModel::DescriptionRole ).toString() );

        QPixmap currentScreenshot = model->data( index, PackageListModel::ScreenshotRole ).value< QPixmap >();
        if ( currentScreenshot.isNull() )
        {
            ui->productScreenshot->setPixmap( m_introduction.screenshot );
        }
        else
        {
            ui->productScreenshot->setPixmap( currentScreenshot );
        }
    }
}

void
PackageChooserPage::updateLabels()
{
    if ( ui && ui->products && ui->products->selectionModel() )
    {
        currentChanged( ui->products->selectionModel()->currentIndex() );
    }
    else
    {
        currentChanged( QModelIndex() );
    }
    emit selectionChanged();
}

void
PackageChooserPage::setModel( QAbstractItemModel* model )
{
    ui->products->setModel( model );
    currentChanged( QModelIndex() );
    connect( ui->products->selectionModel(),
             &QItemSelectionModel::selectionChanged,
             this,
             &PackageChooserPage::updateLabels );
}

void
PackageChooserPage::setSelection( const QModelIndex& index )
{
    if ( index.isValid() )
    {
        ui->products->selectionModel()->select( index, QItemSelectionModel::Select );
    }
    currentChanged( index );
}

bool
PackageChooserPage::hasSelection() const
{
    return ui && ui->products && ui->products->selectionModel() && ui->products->selectionModel()->hasSelection();
}

QStringList
PackageChooserPage::selectedPackageIds() const
{
    if ( !( ui && ui->products && ui->products->selectionModel() ) )
    {
        return QStringList();
    }

    const auto* model = ui->products->model();
    QStringList ids;
    for ( const auto& index : ui->products->selectionModel()->selectedIndexes() )
    {
        QString pid = model->data( index, PackageListModel::IdRole ).toString();
        if ( !pid.isEmpty() )
        {
            ids.append( pid );
        }
    }
    return ids;
}

void
PackageChooserPage::setIntroduction( const PackageItem& item )
{
    m_introduction.name = item.name;
    m_introduction.description = item.description;
    m_introduction.screenshot = item.screenshot;
}
