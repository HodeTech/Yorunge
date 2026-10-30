---
id: P02-0d
phase: P02
status: draft
size: M
depends_on: [P02-0a, P01-2b, P01-3a, P01-5a, P01-5b]
capabilities: [C01, C02, C13]
---
# P02-0d — Platform kimlik, organizasyon ve proje keşfi

**Tarih:** 2026-10-31. **Durum:** Taslak; API key ile raw identity/envelope/pagination/auth teyidi açık. P02-0b üst işinin Platform koludur; [P02-0c LLM](p02-0c-llm-context-discovery.md) bu dış kapıyı beklemez. Aynı nihai PR’dadır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçili Platform API key/hedef için provider principal/account/org anlamını ve açık proje seçiminin doğruluk düzeyini görür. Tarayıcı Bearer çağrıları API key kabulü veya principal alanı kanıtı değildir; görünür proje write izni değildir. Gerçek key/raw sözleşme bilinmeden adapter/verified kimlik uydurulmaz.

## Giren ve girmeyen kapsam

GET auth/me/organizations/projects/seçili projects/{id}; raw kapalı envelope/principal/paging ve anlam teyidi; explicit selection/provider ilişkisi; ayrı discovery variantı ve ortak CLI/API girer. Eksik sayfalama/snapshot garantisi incomplete/unverified, yanlış/boş/çok proje açık kalır. Account profil-only; otomatik seçim/config yazımı yoktur.

Browser JWT fallback, key oluşturma, terms accept, model/kota/dataset taraması, upload/inference, permission uydurma, yeni state/cache ve yeni PR yoktur. Şema kanıtı olmadan fixture’dan sahte production backend yapılmaz.

## Bağımlılıklar ve kararlar

P01/P02-0a bağımlılıkları verified; [Accepted ADR-0020](../../decisions/0020-service-bound-context-discovery.md) yönü kullanıcıca yetkilendirildi. Ready için provider sözleşmesi veya yetkili bounded raw read pilotu her kullanılan endpoint/parametre/hedef kapsamındaki key-auth, raw minimum alanları, account/principal/org anlamını, envelope ve paging’i kapatmalı. Account API semantiği bilinmiyorsa caller tercihi doğrulanamaz. Kullanıcı key/env hazırlığını yaptı; account/project ID bilinmiyor. İlk yetkili /auth/me HTTP200 raw-shape gözlemi auth/principal/envelope/paging kapısını kapatmadı; [hazırlık](../../p02-account-setup.md) sağlanınca salt okuma kanıtı toplanabilir.

## Sözleşme ve uygulama sınırı

[ContextDiscovery](../../reference/context-discovery.md) Platform varyantı raw sözleşme kapanınca aynı kanonik belgede kesinleştirilir; LLM varyantı buna dönüştürülmez. Generic HttpStatusFailure endpoint adaptöründe eşlenir: detail404→selection_unverified/selected_project_not_found; me/list404→invalid_response. Public PII/role/raw body yok; auth kanıtı normalized target/service/endpoint/parametrede kalır. İstekler ağ transaction dışında, mevcut credential/epoch/clock final kapısıyla yürür.

## Kabul

1. Her raw endpoint’in schema/header/envelope/pagination/principal anlamı ve source/target tarihi sabit; malformed2xx veya unknown alanlar kontrollü ret. 403 global unsupported veya kesin invalid-key değildir.
2. Provider explicit auth sözleşmesi yoksa endpoint başına iyi biçimli random negatif kontrol, retry0; 401 veya anlamı kapanmış invalid-key403 gerekir. Malformed reddi, başka endpoint/host/proje kontrolü veya iki2xx auth doğrulaması olmaz. Pilot en çok8 GET/12 attempt/4 MiB/30 s; kontrol key’i registry’ye girmez.
3. Açık/default state kökü no-init; env tek snapshot, final credential/epoch/clock-generation yarışları; TLS/redirect/reflection/deadline/resource cleanup ve CLI/API eşliği gerçek sınırda sınanır.
4. Çok/boş/duplicate/eksik ID, wrong parent, detail404, list404, değişen üyelik/sayfa/cursor; completeness ile atomic consistency ayrımı. İlk UUID yok; birden fazla uzak okumadan atomik snapshot/verified context çıkarılmaz. Sonuç observation aralığı + endpoint zamanlarını taşır.
5. Mevcut31 Ekim review’sindeki bütün ortak kabul ve bütçe/UX/uyumluluk maddeleri P02-0b kartıyla birlikte kapanır. Her adım commit+iki fresh review; gerçek Platform canlı kabulü ve final kaynak test/kurulum/ölçümleri olmadan verified olmaz.

## Doğrulama

Raw contract kapandıktan sonra meaningful unit/contract, gerçek TLS, CLI/subprocess/SQLite iki süreç; statik/tam takım/build/iki kurulum ve kaynak bağlı ölçümler [matrise](../../../CONTRIBUTING.md#doğrulama-seçimi) göre seçilir. Offline fixture ve canlı kaynak ayrı kanıt; başarısız/unknown sonuç saklanır, kimlik/PII/secret repoya konmaz.

## Teslim kaydı

Ürün uygulaması ve tam live kabul yapılmadı. İlk sınırlı /auth/me salt okuma gözlemi paket kaydında; bilinmeyen schema’da diğer uçlar çağrılmadan duruldu. API key/raw sözleşme/erişim kapısı açık; bunun kapanmaması LLM kolunu durdurmaz. Bu alt teslim bitmeden P02-0b/P02-0 tamamlanmış sayılmaz.
