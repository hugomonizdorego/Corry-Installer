/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: a rounded card with a soft, blurred shadow, the building
 *   block of Corry's pages. Neumorphic themes add a light edge on the top left.
 *   Painted with QPainter, so it needs no images and looks the same on Qt 5
 *   and Qt 6. The colors come from the branding stylesheet (qproperty-fill,
 *   qproperty-shadowColor, qproperty-highlight, qproperty-radius).
 */
#ifndef CORRYCARD_H
#define CORRYCARD_H

#include "DllMacro.h"

#include <QColor>
#include <QMargins>
#include <QWidget>

namespace Calamares
{

class UIDLLEXPORT CorryCard : public QWidget
{
    Q_OBJECT
    Q_PROPERTY( QColor fill READ fill WRITE setFill )
    Q_PROPERTY( QColor border READ border WRITE setBorder )
    Q_PROPERTY( QColor shadowColor READ shadowColor WRITE setShadowColor )
    Q_PROPERTY( QColor highlight READ highlight WRITE setHighlight )
    Q_PROPERTY( int radius READ radius WRITE setRadius )
public:
    /** @brief A card with @p padding around its content.
     *
     * The shadow is drawn in the widget's own margins (see shadowMargins()),
     * so the content never overlaps it. Add child widgets to a layout set on
     * the card as usual.
     */
    explicit CorryCard( QWidget* parent = nullptr, const QMargins& padding = QMargins( 28, 24, 28, 24 ) );

    QColor fill() const { return m_fill; }
    void setFill( const QColor& c );
    QColor border() const { return m_border; }
    void setBorder( const QColor& c );
    QColor shadowColor() const { return m_shadowColor; }
    void setShadowColor( const QColor& c );
    /// @brief The light edge of neumorphic themes; transparent for none.
    QColor highlight() const { return m_highlight; }
    void setHighlight( const QColor& c );
    int radius() const { return m_radius; }
    void setRadius( int r );

    /// @brief Shadow softness (blur distance, pixels) and vertical offset.
    void setShadow( int blur, int offsetY );
    /// @brief Space around the card where the shadow is painted.
    QMargins shadowMargins() const { return m_shadowMargins; }
    /// @brief Padding between the card's edge and its content.
    void setPadding( const QMargins& padding );

protected:
    void paintEvent( QPaintEvent* ) override;

private:
    void updateMargins();

    QColor m_fill = QColor( 255, 255, 255 );
    QColor m_border = QColor( 255, 255, 255, 0 );
    QColor m_shadowColor = QColor( 43, 74, 122 );
    QColor m_highlight = QColor( 255, 255, 255, 0 );
    int m_radius = 22;
    int m_blur = 18;
    int m_offsetY = 8;
    QMargins m_shadowMargins;
    QMargins m_padding;
};

}  // namespace Calamares

#endif
