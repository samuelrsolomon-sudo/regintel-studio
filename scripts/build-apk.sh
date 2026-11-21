#!/usr/bin/env bash
set -euo pipefail

rm -rf android-apk-build
mkdir -p android-apk-build/app/src/main/java/com/regintel/studio
mkdir -p android-apk-build/app/src/main/res/layout

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

cat << 'MAN' > android-apk-build/app/src/main/AndroidManifest.xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.INTERNET" />
  <application
    android:label="RegIntel Studio"
    android:usesCleartextTraffic="true"
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
    settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
    webView.setWebViewClient(new WebViewClient());
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

cd android-apk-build
gradle assembleDebug --no-daemon
echo "APK built at: $(pwd)/app/build/outputs/apk/debug/app-debug.apk"
