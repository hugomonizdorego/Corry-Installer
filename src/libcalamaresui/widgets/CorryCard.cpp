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
CorryCard::setRadius( int r )
{
    m_radius = qMax( 0, r );
    update();
}

void
CorryCard::setShadow( int blur, int offsetY, const QColor& color )
{
    m_blur = qMax( 0, blur );
    m_offsetY = offsetY;
    m_shadowColor = color;
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

void
CorryCard::paintEvent( QPaintEvent* )
{
    QPainter painter( this );
    painter.setRenderHint( QPainter::Antialiasing );
    painter.setPen( Qt::NoPen );

    const QRectF card = QRectF( rect() ).marginsRemoved( QMarginsF( m_shadowMargins ) );

    // Soft shadow: concentric rounded rectangles, faint and fading outwards.
    // Together they add up to about 10% darkness right under the card.
    if ( m_blur > 0 )
    {
        const int steps = 16;
        for ( int i = steps; i >= 1; --i )
        {
            const qreal spread = m_blur * i / qreal( steps );
            QColor layer = m_shadowColor;
            const qreal fade = ( steps + 1 - i ) / qreal( steps );  // 1 near the card, small far away
            layer.setAlphaF( 0.017 * fade * fade );
            painter.setBrush( layer );
            painter.drawRoundedRect( card.translated( 0, m_offsetY ).adjusted( -spread, -spread, spread, spread ),
                                     m_radius + spread,
                                     m_radius + spread );
        }
    }

    painter.setBrush( m_fill );
    if ( m_border.alpha() > 0 )
    {
        painter.setPen( QPen( m_border, 1 ) );
    }
    painter.drawRoundedRect( card.adjusted( 0.5, 0.5, -0.5, -0.5 ), m_radius, m_radius );
}

}  // namespace Calamares
