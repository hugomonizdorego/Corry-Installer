/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2022 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "ResultDelegate.h"

#include "Branding.h"
#include "modulesystem/RequirementsModel.h"
#include "utils/Gui.h"

#include <QApplication>
#include <QPainter>
#include <QPainterPath>

static constexpr int const item_margin = 8;
static inline int
item_fontsize()
{
    return Calamares::defaultFontSize() + 4;
}

static inline bool
isCorry()
{
    return Calamares::Branding::instance() && Calamares::Branding::instance()->componentName() == QStringLiteral( "corry" );
}

/** Corry's rows: a soft rounded panel per requirement, tinted amber for a
 * recommendation that is not met and red for a requirement that blocks.
 */
static void
paintCorryRequirement( QPainter* painter, const QStyleOptionViewItem& option, const QModelIndex& index, int role )
{
    const auto fontsize = item_fontsize();
    const bool satisfied = index.data( Calamares::RequirementsModel::Satisfied ).toBool();
    const bool mandatory = index.data( Calamares::RequirementsModel::Mandatory ).toBool();
    const QColor background = satisfied ? QColor( 0xf5, 0xf8, 0xfd ) : mandatory ? QColor( 0xfe, 0xe2, 0xe2 ) : QColor( 0xfe, 0xf3, 0xc7 );
    const QColor text = satisfied ? QColor( 0x1f, 0x2a, 0x44 ) : mandatory ? QColor( 0x99, 0x1b, 0x1b ) : QColor( 0x92, 0x40, 0x0e );
    const auto statusImage = satisfied ? Calamares::StatusOk : mandatory ? Calamares::StatusError : Calamares::StatusWarning;

    painter->setRenderHint( QPainter::Antialiasing );
    QPainterPath panel;
    panel.addRoundedRect( QRectF( option.rect ).adjusted( 0, 3, 0, -3 ), 12, 12 );
    painter->fillPath( panel, background );

    QRect textRect = option.rect.adjusted( item_margin + 6, item_margin, -item_margin, -item_margin );
    QFont font = qApp->font();
    font.setPointSize( fontsize - 2 );
    painter->setFont( font );
    const int iconSize = fontsize + 8;
    const auto image = Calamares::defaultPixmap( statusImage, Calamares::Original, QSize( iconSize, iconSize ) ).toImage();
    painter->drawImage( QPoint( textRect.left(), textRect.center().y() - iconSize / 2 ), image );
    textRect.setLeft( textRect.left() + iconSize + item_margin + 4 );
    painter->setPen( text );
    painter->drawText( textRect, Qt::AlignLeft | Qt::AlignVCenter | Qt::TextSingleLine, index.data( role ).toString() );
}

static void
paintRequirement( QPainter* painter, const QStyleOptionViewItem& option, const QModelIndex& index, int role )
{
    if ( isCorry() )
    {
        paintCorryRequirement( painter, option, index, role );
        return;
    }
    const auto fontsize = item_fontsize();

    QRect textRect = option.rect.adjusted( item_margin, item_margin, -item_margin, -item_margin );
    QFont font = qApp->font();
    font.setPointSize( fontsize );
    font.setBold( false );
    painter->setFont( font );

    Calamares::ImageType statusImage = Calamares::StatusOk;

    painter->setPen( option.palette.text().color() );
    if ( index.data( Calamares::RequirementsModel::Satisfied ).toBool() )
    {
        painter->fillRect( textRect, option.palette.window().color() );
    }
    else
    {
        if ( index.data( Calamares::RequirementsModel::Mandatory ).toBool() )
        {
            QColor bgColor = option.palette.window().color();
            bgColor.setHsv( 0, 64, bgColor.value() );
            painter->fillRect( option.rect, bgColor );
            statusImage = Calamares::StatusError;
        }
        else
        {
            QColor bgColor = option.palette.window().color();
            bgColor.setHsv( 60, 64, bgColor.value() );
            painter->fillRect( option.rect, bgColor );
            statusImage = Calamares::StatusWarning;
        }
    }

    auto image
        = Calamares::defaultPixmap( statusImage, Calamares::Original, QSize( 2 * fontsize, 2 * fontsize ) ).toImage();
    painter->drawImage( textRect.topLeft(), image );

    // Leave space for that image (already drawn)
    textRect.moveLeft( 2 * fontsize + 2 * item_margin );
    painter->drawText( textRect, Qt::AlignLeft | Qt::AlignVCenter | Qt::TextSingleLine, index.data( role ).toString() );
}

QSize
ResultDelegate::sizeHint( const QStyleOptionViewItem& option, const QModelIndex& index ) const
{
    if ( !index.isValid() )
    {
        return option.rect.size();
    }

    QFont font = qApp->font();

    font.setPointSize( item_fontsize() );
    QFontMetrics fm( font );

    const int height = fm.height() + 2 * item_margin + ( isCorry() ? 10 : 0 );
    int textwidth = fm.boundingRect( index.data( Calamares::RequirementsModel::NegatedText ).toString() ).width();

    return QSize( qMax( option.rect.width(), textwidth ), height );
}

void
ResultDelegate::paint( QPainter* painter, const QStyleOptionViewItem& option, const QModelIndex& index ) const
{
    QStyleOptionViewItem opt = option;

    painter->save();

    initStyleOption( &opt, index );
    opt.text.clear();

    paintRequirement( painter, opt, index, m_textRole );

    painter->restore();
}
