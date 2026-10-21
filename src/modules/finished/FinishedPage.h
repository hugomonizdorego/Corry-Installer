/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014-2015 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2017 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#ifndef FINISHEDPAGE_H
#define FINISHEDPAGE_H


#include <QWidget>
#include <QVariantMap>

#include <optional>

class Config;
class QRadioButton;
namespace Ui
{
class FinishedPage;
}  // namespace Ui

class FinishedPage : public QWidget
{
    Q_OBJECT
public:
    explicit FinishedPage( Config* config, QWidget* parent = nullptr );
    void setConfigurationMap( const QVariantMap& configuration );


public slots:
    void onInstallationFailed( const QString& message, const QString& details );
    void retranslate();

protected:
    void focusInEvent( QFocusEvent* e ) override;  //choose the child widget to focus

private:
    Ui::FinishedPage* ui;
    std::optional< QString > m_failure;
    Config* m_config;
    QWidget* m_corryOptions = nullptr;
    QRadioButton* m_continueLive = nullptr;
    QRadioButton* m_restart = nullptr;
    QVariantMap m_corryContent;
};

#endif  // FINISHEDPAGE_H
