/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: soft-shadow card widget.
 */
#include "CorryCard.h"

#include <QPaintEvent>
#include <QPainter>

namespace Calamares
{

CorryCard::CorryCard( QWidget* parent, const QMargins& padding )
    : QWidget( parent )
    , m_padding( padding )
{
    setAttribute( Qt::WA_StyledBackground, false );
    setAutoFillBackground( false );
    updateMargins();
}

void
CorryCard::setFill( const QColor& c )
{
    m_fill = c;
    update();
}

void
CorryCard::setBorder( const QColor& c )
{
    m_border = c;
    update();
}

void
CorryCard::setShadowColor( const QColor& c )
{
    m_shadowColor = c;
    update();
}

void
CorryCard::setHighlight( const QColor& c )
{
    m_highlight = c;
    update();
}

void
CorryCard::setRadius( int r )
{
    m_radius = qMax( 0, r );
    update();
}

void
CorryCard::setShadow( int blur, int offsetY )
{
    m_blur = qMax( 0, blur );
    m_offsetY = offsetY;
    updateMargins();
    update();
}

void
CorryCard::setPadding( const QMargins& padding )
{
    m_padding = padding;
    updateMargins();
}

void
CorryCard::updateMargins()
{
    // The shadow extends blur pixels on every side, plus the offset below.
    m_shadowMargins = QMargins( m_blur, qMax( 0, m_blur - m_offsetY ), m_blur, m_blur + qMax( 0, m_offsetY ) );
    setContentsMargins( m_shadowMargins + m_padding );
}

/// Concentric rounded rectangles, faint and fading outwards: a blurred shadow.
static void
paintSoftShadow( QPainter& painter, const QRectF& card, qreal radius, int blur, QPointF offset, QColor color, qreal strength )
{
    const int steps = 16;
    for ( int i = steps; i >= 1; --i )
    {
        const qreal spread = blur * i / qreal( steps );
        const qreal fade = ( steps + 1 - i ) / qreal( steps );  // 1 near the card, small far away
        QColor layer = color;
        layer.setAlphaF( qBound( 0.0, strength * fade * fade * color.alphaF(), 1.0 ) );
        painter.setBrush( layer );
        painter.drawRoundedRect(
            card.translated( offset ).adjusted( -spread, -spread, spread, spread ), radius + spread, radius + spread );
    }
}

void
CorryCard::paintEvent( QPaintEvent* )
{
    QPainter painter( this );
    painter.setRenderHint( QPainter::Antialiasing );
    painter.setPen( Qt::NoPen );

    const QRectF card = QRectF( rect() ).marginsRemoved( QMarginsF( m_shadowMargins ) );
    if ( m_blur > 0 )
    {
        // Neumorphic themes: a light edge up and to the left ...
        if ( m_highlight.alpha() > 0 )
        {
            paintSoftShadow( painter, card, m_radius, m_blur / 2, QPointF( -m_offsetY / 2.0, -m_offsetY / 2.0 ),
                             m_highlight, 0.09 );
        }
        // ... and every theme: a soft shadow below the card (about 10% darkness under it).
        paintSoftShadow( painter, card, m_radius, m_blur, QPointF( 0, m_offsetY ), m_shadowColor, 0.03 );
    }

    painter.setBrush( m_fill );
    if ( m_border.alpha() > 0 )
    {
        painter.setPen( QPen( m_border, 1 ) );
    }
    painter.drawRoundedRect( card.adjusted( 0.5, 0.5, -0.5, -0.5 ), m_radius, m_radius );
}

}  // namespace Calamares
