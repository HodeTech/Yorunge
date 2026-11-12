---
id: P02-R5
phase: P02
status: blocked
size: M
depends_on: [P02-3m]
capabilities: [C03]
---
# P02-R5 — Dataset öğesi (ve oturum isteyen model ağırlığı) baytlarına programatik erişim

**Tarih:** 2026-11-06. **Sahip:** P02 / datasets modülü. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) dataset öğesi indirmeyi kurmadı; bu kart özgün ihtiyacın (uzak byte doğrulaması) açık sahibidir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı Yörünge ile yüklediği dosyaları uzaktan indirip yerel Manifest’le bağımsız SHA-256 karşılaştırabilmek ister; böylece upload sonucundaki `remote_bytes_verified=false` sınırı kapanır. Gözlem (4 Kasım 2026, tek hesap): öğenin `file_url` değeri API anahtarıyla 401 “Oturum gerekli” verdi; kamu web istemcisi dosyaları kullanıcı oturum JWT’siyle çeker ve öğe başına bayt rotası yoktur. Anahtarla çalışan tek bayt yolları ZIP export/ücretli hazırlık rotalarıdır.

## Giren ve girmeyen kapsam

Sağlayıcının API anahtarıyla veya başka kapsamlı resmî programatik kimlikle erişilebilir bir öğe-bayt yolu sunduğunun bağımsız gözlenmesi; sonra bu yolu P02-3b motoruna bağlayan tüketici ve manifest karşılaştırmalı doğrulama girer. Oturum JWT’sini tarayıcıdan almak/saklamak, çerez taklidi, ZIP export’u örtük indirme saymak, SDK kodunu çalıştırmak ve otomatik ücretli export girmez.

## Bağımlılıklar ve kararlar

Açılma ölçütü (dış koşul veya ürün kararı): (a) sağlayıcının resmî bir API-key erişimli öğe indirme/imzalı URL yolu sunması, (b) kullanıcının ayrı bir kimlik yöntemini ve saklama/yetki modelini ADR ile onaylaması veya (c) kullanıcı onaylı, ücreti önceden gösterilen export tabanlı doğrulamanın (sürüm gerektirir; `export/download` ZIP, biçim/ad eşlemesi ve arşiv güvenliği için ayrı araştırma/ADR) kabul edilmesi; üçü de bugün yoktur. (c) ürün kararıdır ve P02-3 planındaki K4’te sorulur. P02-3b motoru ve doğrulama sözlüğü hazır olduğundan koşul gerçekleşince tüketici dar bir iştir. Faz kabulü 1. madde (indirme/verify) dataset baytları için bu karta bağlıdır; kapalıysa P02-7 bunu `partial` ve açılma koşuluyla kaydeder, kapsamı sessizce küçültmez.

## Sözleşme ve uygulama sınırı

**Model ağırlığı kapsamı:** model indirme yoklaması (ADR-0032 §1) imzalı URL’nin oturum istediğini gösterirse aynı açılma ölçütleri model ağırlığı baytları için de bu kartta aranır (yeni kart açılmaz). Sağlayıcı yolu kanıtlanana kadar sözleşme tanımlanmaz. Doğrulama P02-3b seviyelerini (`local_manifest` kaynaklı `sha256_matched`) kullanır; upload kayıtlarının `remote_bytes_verified` alanı bu kartla otomatik değişmez, ayrı kontrat değişikliği ister.

## Kabul

1. Gerçek bir öğe, API-key erişimli resmî yoldan indirilir, yerel Manifest özetiyle bağımsız karşılaştırılır; uyuşmazlık başarı sayılmaz.
2. Yetki yok/oturum gerekli sonucu açık `remote_access_denied` kalır; kimlik taklidi yoktur.
3. İki fresh review turu ve önceden sınırlanmış yetkili canlı kabul olmadan verified olmaz.

## Doğrulama

Önce kaynak/gözlem (GET yalnız, kullanıcı yetkisiyle, istek sayısı ve hedef önceden yazılı); sonra dar kod/test. Eski 401 gözlemi yeni sürümde yeniden doğrulanmadan kalıcı sayılmaz.

## Teslim kaydı

Blocked; sağlayıcı yolu, kod veya canlı kabul yoktur. Açılma ölçütü yukarıda isimlidir.
