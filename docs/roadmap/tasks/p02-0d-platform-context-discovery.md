---
id: P02-0d
phase: P02
status: in_progress
size: M
depends_on: [P02-0a, P01-2b, P01-3a, P01-5a, P01-5b]
capabilities: [C01, C02, C13]
---
# P02-0d — Platform kimlik, organizasyon ve proje keşfi

**Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **Durum:** Ara unverified uygulama in_progress; üç endpoint için yeni metadata gözlemi var, auth/principal/pagination ve dolu/seçili proje teyidi açık. ADR-0021 2026-11-01 kullanıcı onayıyla Accepted; onay commit’inden sonra adım5.1 çekirdeği iki fresh review turuyla kapandı; adım5.2 public API/CLI ve kurulu paket testi sürüyor. P02-0b üst işinin Platform koludur; [P02-0c LLM](p02-0c-llm-context-discovery.md) bu dış kapıyı beklemez. Aynı nihai PR’dadır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçili Platform API key/hedef için provider principal/account/org anlamını ve açık proje seçiminin doğruluk düzeyini görür. Tarayıcı Bearer çağrıları API key kabulü veya principal alanı kanıtı değildir; görünür proje write izni değildir. Gerçek key/raw sözleşme bilinmeden adapter/verified kimlik uydurulmaz.

## Giren ve girmeyen kapsam

GET auth/me/organizations/projects/seçili projects/{id}; raw kapalı envelope/principal/paging ve anlam teyidi; explicit selection/provider ilişkisi; ayrı discovery variantı ve ortak CLI/API girer. Eksik sayfalama/snapshot garantisi incomplete/unverified, yanlış/boş/çok proje açık kalır. Account profil-only; otomatik seçim/config yazımı yoktur.

Browser JWT fallback, key oluşturma, terms accept, model/kota/dataset taraması, upload/inference, permission uydurma, yeni state/cache ve yeni PR yoktur. Şema kanıtı olmadan fixture’dan sahte production backend yapılmaz.

## Bağımlılıklar ve kararlar

P01/P02-0a bağımlılıkları verified. **Bugün** [ADR-0020](../../decisions/0020-service-bound-context-discovery.md) Accepted ve bağlayıcıdır; nihai verified için provider sözleşmesi veya yetkili tam contract pilotuyla raw/key/identity/envelope/pagination kapısı korunur; ara uygulama başlangıcını Accepted ADR-0021 açar. Kullanıcı key/env hazırlığını yaptı; başlangıç liste okumaları için account/project ID gerekmedi. Mevcut tür receipt’i parser uyumunu veya auth’u kanıtlamaz.

**ADR-0021 Accepted:** [kapalı ara projeksiyon](../../reference/context-discovery.md#önerilen-platform-gözlem-varyantı) ve aynı commit’teki belge geçişleriyle bu kart yalnız unverified gözlem kodlamasına ready oldu. Bu, aşağıdaki nihai verified/live kapısını kaldırmaz. Kart ve P02-0b/P02-0, ara kod/test başarılı diye verified olmaz. Tam provider sözleşmesi kapanınca üretimdeki raw parser’ın katı decoder’a geçirilmesi ek zorunlu kod adımıdır; katı ret sonrası projeksiyona fallback yoktur.

[Yeni metadata gözlemleri](../../research/p02-platform-discovery-observations.md) me success=true, organizations items/total türü ve boş projects cevabını kaydeder. Birikimli5 GET sapması contract kabulü değildir. [ADR-0021](../../decisions/0021-platform-discovery-observations.md) **Accepted**; kullanıcı revizyonu açıkça onayladı. Yalnız ara başlangıç kapısı değişti.

## Sözleşme ve uygulama sınırı

[ContextDiscovery](../../reference/context-discovery.md) Platform bölümü Accepted tasarımdır; ara consumer ve nihai katı parser sınırı aynı belgede tutulur. LLM varyantı değişmez. Detail404 için ADR-0020’nin kavramsal selection_unverified ifadesinin [önerilen kesin wire eşlemesi](../../reference/context-discovery.md#seçim-kavramları-ve-kapalı-wire-eşlemesi) validation=unverified + projects.selection.state=not_found + selected_project_not_found’dur; selection_unverified adında ayrı wire alanı/değeri yoktur. Me/list404 invalid_response; yanlış detail ID de invalid_response. Parent/hesap farkları doğrulanmış membership veya izin olarak yorumlanmaz.

Tüketilmeyen ad/email/telefon/diğer profil alanları, ham role/admin_permissions ve raw body yayımlanmaz. Yayımlanan opak ID’ler kişiye bağlanabilir; “tüm kişisel veri ayıklandı” vaadi yoktur. İstekler transaction dışında, aynı tek credential/config snapshot ve final gate ile yürür. Profilden veya açık override’dan gelen selected.project_id detail GET’i tetikler; profile_preference orijinal profili korur. API overload ve iki-varyant CLI renderer sözleşmesi koddan önce referansta kapalıdır.

## Kabul

Bu iki aşamalı ayrım 2026-11-01 ADR-0021 onayıyla etkindir; nihai verified kapısı korunur.

1. **Ara gözlem uygulaması:** tüketilen raw alan/control eksik veya yanlışsa invalid_response; tüketilmeyen metadata tam raw-tree JSON/sır taraması sonrası atılır, ret beklenmez. Public wire extra=forbid/strict kalır. **Nihai verified:** provider-version/endpoint schema/header/envelope/pagination/principal anlamı ve source/target tarihi kapanır; üretimde projeksiyon-only parser katı decoder ile değiştirilir ve raw unknown alan ret olur. Bu ek ürün değişikliği ve regresyonları olmadan verified olmaz; yalnız bir kabul helper’ını sıkılaştırmak yetmez.403 global unsupported veya kesin invalid-key değildir.
2. Provider explicit auth sözleşmesi yoksa endpoint başına iyi biçimli random negatif kontrol, retry0; 401 veya anlamı kapanmış invalid-key403 gerekir. Malformed reddi, başka endpoint/host/proje kontrolü veya iki2xx auth doğrulaması olmaz. Pilot en çok8 GET/12 attempt/4 MiB/30 s; kontrol key’i registry’ye girmez.
3. Açık/default state kökü no-init; env tek snapshot, final credential/epoch/clock-generation yarışları; TLS/redirect/reflection/deadline/resource cleanup ve CLI/API eşliği gerçek sınırda sınanır.
4. Çok/boş/duplicate/eksik ID; profile-only project için4, project yoksa 3 GET; explicit override’da profile_preference/selected ayrı; detail404 eşleme ve tam ASCII-sıralı reason dizisi. Profil account-parent farkı veya aynı ID’nin list/detail parent farkı normal unverified sonuçtur; iki kaynak ayrı korunur, membership/mismatch uydurulmaz. Yanlış detail ID invalid_response’dur. List404, değişen üyelik/sayfa/cursor; completeness ile atomic consistency ayrımı sınanır. İlk UUID seçilmez; sonuç observation aralığı + endpoint zamanlarını taşır.
5. Mevcut31 Ekim review’sindeki bütün ortak kabul ve bütçe/UX/uyumluluk maddeleri P02-0b kartıyla birlikte kapanır. Her adım commit+iki fresh review; gerçek Platform canlı kabulü ve final kaynak test/kurulum/ölçümleri olmadan verified olmaz.

## Doğrulama

Ara kodlamada ADR-0021 onayı sonrası meaningful unit/contract, gerçek TLS, CLI/subprocess/SQLite iki süreç; statik/tam takım/build/iki kurulum ve kaynak bağlı ölçümler [matrise](../../../CONTRIBUTING.md#doğrulama-seçimi) göre seçilir. Nihai strict decoder ve gerçek hizmet kabulü raw/key/identity/pagination kaynağını ayrıca gerektirir. Offline fixture ve canlı kaynak ayrı kanıt; başarısız/unknown sonuç saklanır, gerçek profil alanları/key/ham response repoya konmaz. Public çıktıda amaçlanan sentetik/gerçek ID referanslarının kişiye bağlanabilirliği ayrı anlatılır.

## Teslim kaydı

Ürün uygulaması ve tam live kabul yapılmadı. İlk sınırlı /auth/me gözlemini takip eden üç-endpoint metadata survey paket kaydında; bunlar parser veya auth kabulü değildir. 1 Kasım kullanıcı review’si sonrası öneri revize edildi, ADR-0021 halen Proposed. API key/raw sözleşme/erişim kapısı açık; bunun kapanmaması LLM kolunu durdurmaz. Bu alt teslim bitmeden P02-0b/P02-0 tamamlanmış sayılmaz.
