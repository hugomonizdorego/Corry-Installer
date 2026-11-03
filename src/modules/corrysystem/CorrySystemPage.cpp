/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: the "Init system" and "Boot loader" pages.
 */
#include "CorrySystemPage.h"

#include "utils/Retranslator.h"

#include <QGridLayout>
#include <QHBoxLayout>
#include <QKeyEvent>
#include <QLabel>
#include <QMouseEvent>
#include <QPushButton>
#include <QRadioButton>
#include <QCoreApplication>
#include <QStyle>
#include <QVBoxLayout>

namespace CorrySystem
{

static QLabel*
badge( const QString& text, const char* objectName, QWidget* parent )
{
    auto* label = new QLabel( text, parent );
    label->setObjectName( QString::fromLatin1( objectName ) );
    return label;
}

OptionCard::OptionCard( const Option& option, QWidget* parent )
    : QFrame( parent )
    , m_id( option.id )
    , m_radio( new QRadioButton( this ) )
{
    setObjectName( QStringLiteral( "corryOption" ) );
    setProperty( "selected", false );
    setCursor( option.available ? Qt::PointingHandCursor : Qt::ForbiddenCursor );
    setFocusPolicy( option.available ? Qt::StrongFocus : Qt::NoFocus );
    setAccessibleName( option.name );
    setEnabled( option.available );
    m_radio->setFocusPolicy( Qt::NoFocus );
    m_radio->setAutoExclusive( false );
    m_radio->setAccessibleName( option.name );

    auto* row = new QHBoxLayout( this );
    row->setContentsMargins( 14, 10, 14, 10 );
    row->setSpacing( 12 );
    row->addWidget( m_radio, 0, Qt::AlignTop );
    auto* column = new QVBoxLayout;
    column->setSpacing( 3 );
    row->addLayout( column, 1 );

    auto* head = new QHBoxLayout;
    head->setSpacing( 6 );
    auto* title = new QLabel( option.name, this );
    title->setObjectName( QStringLiteral( "corryOptionTitle" ) );
    head->addWidget( title );
    for ( const auto& text : option.badges )
    {
        // The same texts as Config::evaluate*() uses for its badges.
        const auto corry = []( const char* source ) { return QCoreApplication::translate( "Corry", source ); };
        const bool warning = text == corry( "Needs internet" ) || text == corry( "Needs systemd" );
        const bool muted = text == corry( "Works offline" ) || text == corry( "UEFI only" ) || text == corry( "BIOS only" );
        head->addWidget(
            badge( text, warning ? "corryBadgeWarning" : muted ? "corryBadgeMuted" : "corryBadge", this ) );
    }
    head->addStretch();
    column->addLayout( head );

    auto* text = new QLabel( option.description, this );
    text->setObjectName( QStringLiteral( "corryOptionText" ) );
    text->setWordWrap( true );
    column->addWidget( text );
    if ( !option.reason.isEmpty() )
    {
        auto* reason = new QLabel( option.reason, this );
        reason->setObjectName( QStringLiteral( "corryOptionReason" ) );
        reason->setWordWrap( true );
        column->addWidget( reason );
    }
    connect( m_radio,
             &QRadioButton::clicked,
             this,
             [ this ]
             {
                 // A click on the ticked radio would untick it (not auto-exclusive):
                 // the card's state decides, the page re-ticks after the choice.
                 m_radio->setChecked( property( "selected" ).toBool() );
                 emit chosen( m_id );
             } );
}

void
OptionCard::setSelected( bool selected )
{
    m_radio->setChecked( selected );
    setProperty( "selected", selected );
    style()->unpolish( this );
    style()->polish( this );
    update();
}

void
OptionCard::mousePressEvent( QMouseEvent* event )
{
    if ( isEnabled() && event->button() == Qt::LeftButton )
    {
        emit chosen( m_id );
    }
    QFrame::mousePressEvent( event );
}

void
OptionCard::keyPressEvent( QKeyEvent* event )
{
    if ( event->key() == Qt::Key_Space || event->key() == Qt::Key_Return || event->key() == Qt::Key_Enter )
    {
        emit chosen( m_id );
        return;
    }
    QFrame::keyPressEvent( event );
}

CorrySystemPage::CorrySystemPage( Config* config, QWidget* parent )
    : QWidget( parent )
    , m_config( config )
{
    // ViewManager puts every Corry page in a scroll area; this page needs none of its own.
    m_layout = new QVBoxLayout( this );
    m_layout->setContentsMargins( 0, 0, 0, 0 );
    m_layout->setSpacing( 12 );
    auto* statusRow = new QHBoxLayout;
    statusRow->setSpacing( 12 );
    m_status = new QLabel( this );
    m_status->setObjectName( QStringLiteral( "corryHint" ) );
    m_status->setWordWrap( true );
    statusRow->addWidget( m_status, 1 );
    auto* recheck = new QPushButton( this );
    recheck->setObjectName( QStringLiteral( "corryRecheckButton" ) );
    CALAMARES_RETRANSLATE( recheck->setText( tr( "Check again" ) );
                           recheck->setToolTip( tr( "Test the internet connection again and refresh the options." ) ); );
    connect( recheck, &QPushButton::clicked, this, [ this ] { m_config->evaluate( detectEnvironment( true ) ); } );
    statusRow->addWidget( recheck, 0, Qt::AlignTop );
    m_layout->addLayout( statusRow );
    m_hint = new QLabel( this );
    m_hint->setObjectName( QStringLiteral( "corryHint" ) );
    m_hint->setWordWrap( true );
    m_layout->addWidget( m_hint );
    m_grid = new QGridLayout;
    m_grid->setHorizontalSpacing( 12 );
    m_grid->setVerticalSpacing( 10 );
    m_grid->setColumnStretch( 0, 1 );
    m_grid->setColumnStretch( 1, 1 );
    m_layout->addLayout( m_grid );
    m_layout->addStretch( 1 );
    connect( m_config, &Config::changed, this, &CorrySystemPage::rebuild );
    rebuild();
}

void
CorrySystemPage::rebuild()
{
    // A selection change only re-ticks the cards; a new evaluation rebuilds them.
    if ( !m_cards.isEmpty() && m_builtEvaluation == m_config->evaluation() )
    {
        for ( auto* card : std::as_const( m_cards ) )
        {
            card->setSelected( card->id() == m_config->selected() );
        }
        return;
    }
    m_builtEvaluation = m_config->evaluation();
    // The cards are deleted later: one of them may be emitting the signal that got us here.
    for ( auto* card : std::as_const( m_cards ) )
    {
        m_grid->removeWidget( card );
        card->hide();
        card->deleteLater();
    }
    m_cards.clear();

    const auto environment = m_config->environment();
    m_status->setText( environment.online
                           ? tr( "<b>Online.</b> Every option can be downloaded. Computer: %1, %2%3." )
                                 .arg( environment.firmware == QStringLiteral( "efi" ) ? tr( "UEFI" ) : tr( "BIOS" ),
                                       environment.architecture,
                                       environment.secureBoot ? tr( ", Secure Boot on" ) : QString() )
                           : tr( "<b>Offline.</b> Only the default can be installed. Connect to the internet, "
                                 "then press Check again to enable the alternatives." ) );
    m_hint->setText( m_config->section() == Config::Section::Init
                         ? tr( "The alternatives replace systemd with elogind for sessions, dbus-x11 for the "
                               "session bus, rsyslog for logs and cron for timers. If the switch is not possible, "
                               "the new system keeps systemd and the log says why." )
                         : tr( "When an alternative is chosen, it is installed and checked first; only then is GRUB "
                               "removed from the new system. If anything fails, GRUB is installed instead and the "
                               "log says why." ) );
    int index = 0;
    for ( const auto& option : m_config->options() )
    {
        auto* card = new OptionCard( option, this );
        card->setSelected( option.id == m_config->selected() );
        connect( card, &OptionCard::chosen, this, [ this ]( const QString& id ) { m_config->select( id ); } );
        m_grid->addWidget( card, index / 2, index % 2 );
        m_cards.append( card );
        ++index;
    }
}

}  // namespace CorrySystem
