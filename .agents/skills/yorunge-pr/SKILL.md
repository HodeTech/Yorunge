---
name: yorunge-pr
description: Yörünge'de yetkilendirilmiş değişikliği commit, development PR, CI takibi ve uygun merge commit ile tamamla. Salt analizde dış işlem başlatma; Master aktarımı, release veya repo izin ayarı yapma.
---
# Yörünge PR akışını tamamla

[Kanonik Git standardını](../../../docs/standards/git-release.md) oku. Mevcut kullanıcı isteği commit/PR işlemini kapsıyor mu değerlendir; skill çağrısını yayın, mesaj gönderme veya repo yönetim izni sayma.

1. Çalışma ağacını ve tabanı doğrula. Yeni iş güncel `origin/development` üzerinden kısa ömürlü dalda olmalı. Kullanıcı dosyalarını koru; yalnız kendi değişikliklerini stage et, kör `git add -A` veya force push kullanma.
2. İstenen sonucu ve doğrulamayı commit et. Türkçe açıklama ve İngilizce teknik kimlikler kullan. PR başlığı/gövdesi final diff'i anlatsın; çok satırlı gövdeyi yapılandırılmış argüman veya `--body-file` ile ver.
3. Mevcut PR varsa onu güncelle; belirsiz oluşturma/gönderim hatasında tekrar denemeden önce uzak durumu oku. Connector ilgili yeteneği sunmuyorsa izinli CLI yolunu kullan; anahtarı/gövdeyi loga dökme.
4. PR hedefi `development`; zorunlu `offline-core` ve `branch-policy` sonuçlarını son head üzerinde bekle. Gerçek review bulgusunu düzeltmeden konuşmayı kapatma. Aynı kontrolü başarısızlığı gizlemek için tekrar tekrar başlatma.
5. Birleştirme yetkili işin kapsamındaysa güncel head'i sabitleyip merge commit kullan. `--admin`/bypass, squash veya rebase merge yoktur. Başka değişiklik geldiyse incelemeden aynı komutu tekrar etme.
6. Uzak merge/parent ve CI sonucunu doğrula, yerel development'ı yalnız güvenli fast-forward ile güncelle. Yerel commit, push, PR, merge ve yayın farklı durumlardır; hangisinin oluştuğunu açık yaz.

`Master` hedefi yalnız aynı deponun development dalından olabilir; bu skill Master'ı birleştirmez veya tag/release yayımlamaz. Kullanıcının mevcut yetkisini aşan yönetim işlemini sıradan PR işine ekleme.
