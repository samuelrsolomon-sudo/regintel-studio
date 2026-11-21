#!/usr/bin/env bash
set -euo pipefail

rm -rf android-apk-build
mkdir -p android-apk-build/app/src/main/java/com/regintel/studio
mkdir -p android-apk-build/app/src/main/res/layout
mkdir -p android-apk-build/app/src/main/res/xml

cat << 'GRADLE' > android-apk-build/settings.gradle
rootProject.name = "RegIntelStudio"
include ':app'
GRADLE

cat << 'PGR' > android-apk-build/gradle.properties
org.gradle.jvmargs=-Xmx2048m
android.useAndroidX=true
GRADLE

cat << 'BGR' > android-apk-build/build.gradle
buildscript {
  repositories {
    google()
    mavenCentral()
  }
  dependencies {
    classpath 'com.android.tools.build:gradle:8.5.2'
  }
}
allprojects {
  repositories {
    google()
    mavenCentral()
  }
}
GRADLE

cat << 'AGR' > android-apk-build/app/build.gradle
plugins {
  id 'com.android.application'
}
android {
  namespace 'com.regintel.studio'
  compileSdk 34
  defaultConfig {
    applicationId "com.regintel.studio"
    minSdk 24
    targetSdk 34
    versionCode 1
    versionName "1.0.0"
  }
  buildTypes {
    release {
      minifyEnabled false
    }
  }
  compileOptions {
    sourceCompatibility JavaVersion.VERSION_17
    targetCompatibility JavaVersion.VERSION_17
  }
}
dependencies {
  implementation 'androidx.appcompat:appcompat:1.7.0'
  implementation 'androidx.webkit:webkit:1.11.0'
}
AGR

cat << 'NSC' > android-apk-build/app/src/main/res/xml/network_security_config.xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="false">127.0.0.1</domain>
    <domain includeSubdomains="false">localhost</domain>
  </domain-config>
</network-security-config>
NSC

cat << 'MAN' > android-apk-build/app/src/main/AndroidManifest.xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.INTERNET" />
  <application
    android:label="RegIntel Studio"
    android:usesCleartextTraffic="true"
    android:networkSecurityConfig="@xml/network_security_config"
    android:theme="@style/Theme.AppCompat.Light.NoActionBar">
    <activity
      android:name=".MainActivity"
      android:exported="true"
      android:configChanges="orientation|screenSize|keyboardHidden">
      <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
      </intent-filter>
    </activity>
  </application>
</manifest>
MAN

cat << 'LAY' > android-apk-build/app/src/main/res/layout/activity_main.xml
<?xml version="1.0" encoding="utf-8"?>
<WebView xmlns:android="http://schemas.android.com/apk/res/android"
  android:id="@+id/webview"
  android:layout_width="match_parent"
  android:layout_height="match_parent" />
LAY

cat << 'JAVA' > android-apk-build/app/src/main/java/com/regintel/studio/MainActivity.java
package com.regintel.studio;

import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
  private WebView webView;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_main);
    webView = findViewById(R.id.webview);
    WebSettings settings = webView.getSettings();
    settings.setJavaScriptEnabled(true);
    settings.setDomStorageEnabled(true);
    settings.setAllowFileAccess(true);
    settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
    settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
    webView.clearCache(true);

    webView.setWebViewClient(new WebViewClient() {
      @Override
      public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        return false;
      }

      @Override
      public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
        if (request != null && request.isForMainFrame() && errorResponse != null) {
          String msg = "HTTP " + errorResponse.getStatusCode() + " loading " + request.getUrl();
          String escaped = msg.replace("\\", "\\\\").replace("'", "\\'");
          view.evaluateJavascript("document.body.insertAdjacentHTML('afterbegin', '<div style=\"background:#7f1d1d;color:#fecaca;padding:8px;font-size:12px;\">" + escaped + "</div>');", null);
        }
      }

      @Override
      public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
        if (request != null && request.isForMainFrame() && error != null) {
          String msg = "WebView error (" + error.getErrorCode() + "): " + error.getDescription() + " on " + request.getUrl();
          String escaped = msg.replace("\\", "\\\\").replace("'", "\\'");
          view.evaluateJavascript("document.body.insertAdjacentHTML('afterbegin', '<div style=\"background:#7f1d1d;color:#fecaca;padding:8px;font-size:12px;\">" + escaped + "</div>');", null);
        }
      }
    });
    webView.setWebChromeClient(new WebChromeClient());
    webView.loadUrl("http://127.0.0.1:8080/");
  }

  @Override
  public void onBackPressed() {
    if (webView != null && webView.canGoBack()) {
      webView.goBack();
    } else {
      super.onBackPressed();
    }
  }
}
JAVA

if [ -d "app/build/outputs/apk/debug" ] || [ -f "gradlew" ]; then
  gradle assembleDebug --no-daemon || true
fi
echo "Updated scripts/build-apk.sh"

pushd android-apk-build >/dev/null
if command -v gradle >/dev/null 2>&1; then
  gradle wrapper --gradle-version 8.7 --no-daemon || true
fi
if [ -x "./gradlew" ]; then
  chmod +x ./gradlew
  ./gradlew assembleDebug --no-daemon
elif command -v gradle >/dev/null 2>&1; then
  gradle assembleDebug --no-daemon
else
  echo "ERROR: Neither ./gradlew nor gradle found on runner"
  exit 1
fi
ls -lh app/build/outputs/apk/debug/app-debug.apk
popd >/dev/null
