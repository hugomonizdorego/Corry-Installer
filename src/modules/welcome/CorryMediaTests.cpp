// SPDX-License-Identifier: GPL-3.0-or-later
#include <QAudioDecoder>
#include <QAudioBuffer>
#include <QQmlContext>
#include <QQuickWidget>
#include <QQuickItem>
#include <QtTest>

class CorryMediaTests : public QObject
{
    Q_OBJECT
private slots:
    void welcomeAndSlideshow()
    {
        const QString brand = qEnvironmentVariable( "CORRY_TEST_BRAND_DIR" );
        QVERIFY2( !brand.isEmpty(), "Set CORRY_TEST_BRAND_DIR to a compiled distro branding folder" );
        QQuickWidget view;
        view.rootContext()->setContextProperty( "corryQtMajorVersion", QT_VERSION_MAJOR );
        view.resize( 600, 400 );
        view.setSource( QUrl::fromLocalFile( brand + "/WelcomeMedia.qml" ) );
        QTRY_COMPARE( view.status(), QQuickWidget::Ready );
        QObject* root = view.rootObject();
        QVERIFY( root );
        QVERIFY( !root->property( "isPlaying" ).toBool() );
        QVERIFY( QMetaObject::invokeMethod( root, "togglePlayback" ) );
        QTRY_VERIFY_WITH_TIMEOUT( root->property( "isPlaying" ).toBool(), 15000 );
        QVERIFY( !root->property( "mediaFailed" ).toBool() );
        QVERIFY( QMetaObject::invokeMethod( root, "onLeave" ) );
        QTRY_VERIFY( !root->property( "isPlaying" ).toBool() );
        root->setProperty( "autoplay", true );
        QMetaObject::invokeMethod( root, "onActivate" );
        QTRY_VERIFY( root->property( "isPlaying" ).toBool() );
        QMetaObject::invokeMethod( root, "onLeave" );
        QTRY_VERIFY( !root->property( "isPlaying" ).toBool() );
        root->setProperty( "videoSource", "video/does-not-exist.webm" );
        QMetaObject::invokeMethod( root, "togglePlayback" );
        QTRY_VERIFY_WITH_TIMEOUT( root->property( "mediaFailed" ).toBool(), 15000 );
        QCOMPARE( view.status(), QQuickWidget::Ready ); // Failed media keeps the welcome usable.

        view.setSource( QUrl::fromLocalFile( brand + "/show.qml" ) );
        QTRY_COMPARE( view.status(), QQuickWidget::Ready );
        root = view.rootObject();
        root->setProperty( "musicVolume", 0.0 );
        QMetaObject::invokeMethod( root, "onActivate" );
        QTRY_VERIFY_WITH_TIMEOUT( root->property( "musicPlaying" ).toBool(), 15000 );
        QVERIFY( !root->property( "musicFailed" ).toBool() );
        root->setProperty( "musicEnabled", false );
        QTRY_VERIFY( !root->property( "musicPlaying" ).toBool() );
        root->setProperty( "musicEnabled", true );
        QTRY_VERIFY( root->property( "musicPlaying" ).toBool() );
        QMetaObject::invokeMethod( root, "onLeave" );
        QTRY_VERIFY( !root->property( "musicPlaying" ).toBool() );
        QVERIFY( !root->property( "active" ).toBool() );
    }

    void decodeMusic()
    {
        QAudioDecoder decoder;
        bool decoded = false;
        connect( &decoder, &QAudioDecoder::bufferReady, this, [&] {
            const QAudioBuffer buffer = decoder.read();
            decoded = decoded || ( buffer.isValid() && buffer.byteCount() > 0 );
        } );
        const QString path = qEnvironmentVariable( "CORRY_TEST_BRAND_DIR" ) + "/music/installation.ogg";
#if QT_VERSION_MAJOR >= 6
        decoder.setSource( QUrl::fromLocalFile( path ) );
#else
        decoder.setSourceFilename( path );
#endif
        decoder.start();
        QTRY_VERIFY_WITH_TIMEOUT( decoded, 15000 );
        QCOMPARE( decoder.error(), QAudioDecoder::NoError );
        decoder.stop();
    }
};

QTEST_MAIN( CorryMediaTests )
#include "CorryMediaTests.moc"
