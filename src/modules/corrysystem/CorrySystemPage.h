/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: the "Init system" and "Boot loader" pages.
 */
#ifndef CORRYSYSTEMPAGE_H
#define CORRYSYSTEMPAGE_H

#include "Config.h"

#include <QFrame>
#include <QWidget>

class QGridLayout;
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
    Config* m_config;
    QVBoxLayout* m_layout = nullptr;
    QGridLayout* m_grid = nullptr;
    QLabel* m_status = nullptr;
    QLabel* m_hint = nullptr;
    QList< OptionCard* > m_cards;
    int m_builtEvaluation = -1;
};

}  // namespace CorrySystem

#endif
