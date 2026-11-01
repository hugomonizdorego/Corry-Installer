/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: the "System components" page.
 */
#ifndef CORRYSYSTEMPAGE_H
#define CORRYSYSTEMPAGE_H

#include "Config.h"

#include <QFrame>
#include <QWidget>

class QLabel;
class QRadioButton;
class QVBoxLayout;

namespace CorrySystem
{

/// A selectable card: name, badges, description and, when unavailable, the reason.
class OptionCard : public QFrame
{
    Q_OBJECT
public:
    OptionCard( const Option& option, QWidget* parent = nullptr );
    QString id() const { return m_id; }
    void setSelected( bool selected );

signals:
    void chosen( const QString& id );

protected:
    void mousePressEvent( QMouseEvent* event ) override;
    void keyPressEvent( QKeyEvent* event ) override;

private:
    QString m_id;
    QRadioButton* m_radio;
};

class CorrySystemPage : public QWidget
{
    Q_OBJECT
public:
    explicit CorrySystemPage( Config* config, QWidget* parent = nullptr );

public slots:
    /// @brief Rebuild the cards from the configuration's current state.
    void rebuild();

private:
    void addSection( QVBoxLayout* into, const QString& title, const QString& text, const QList< Option >& options,
                     const QString& selected, bool isInit );

    Config* m_config;
    QWidget* m_content = nullptr;
    QVBoxLayout* m_contentLayout = nullptr;
    QLabel* m_status = nullptr;
    QList< OptionCard* > m_initCards;
    QList< OptionCard* > m_bootCards;
};

}  // namespace CorrySystem

#endif
