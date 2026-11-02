# Oluşturulmuş kaydı salt okumayla inceleme hazırlığı

**Tarih:** 2026-11-02. Önceki [ilk pilot](../../p02-2-private-create-observations.md) detail GET 405 nedeniyle durdu; create veya upload tekrar edilmez. Bu ayrı, henüz çalıştırılmamış takip yalnız private journal'daki **aynı dataset** içindir. Yeni hesap çağrı yetkisi olmadan execute edilmez.

En çok **3 mantıksal GET / 6 HTTP denemesi / 1,5 MiB tüketilen raw response / 30 s**:

1. `GET datasets?page=1&page_size=5&scope=owned`; ilk sayfada journal'daki exact ID tekil bulunmalı.
2. Yalnız o kayıttan alınan ve güvenli path bileşeni olarak doğrulanan `owner_username`/`slug` ile `GET datasets/{owner_username}/{slug}`; ID/private/name/owner-org eşliği kontrol edilir. Bu araştırmada iki kayıtta `org_id` açıkça bulunmalı ve null veya aynı canonical UUID olmalıdır; eksik alan kişisel sahiplik kanıtına çevrilmez.
3. Aynı canonical ID için `GET datasets/{id}/my-role`; yalnız tipler ve `upload` string'inin listede bulunması gözlenir.

Liste büyütme, sayfalama, başka dataset seçme, POST/PUT/DELETE, proje bağlantısı, upload, terms, billing veya ham hesap verisi saklama yoktur. İlk hata/limit/mismatch'te durulur. Sonuç verified identity/grant/cost veya önceki pilotun başarılı kabulü değildir. Exclusive yeni private kayıt reentry'yi reddeder; public receipt yalnız tip/sayaç/predicate taşır. Source/test ve kullanılan frozen helper SHA bağı kaydedilir. Hash'i doğrulanan aynı helper byte buffer'ı derlenip ayrı namespace'te yürütülür; import/pyc/yüklenmiş modül önbelleği bu bağı değiştiremez.

```sh
.venv/bin/python -m pytest docs/research/probes/platform-created-dataset-read-20261102/test_read_probe.py -q
```

Kaynak review ve kullanıcı tarafından bu somut scope'un onayı kapanmadan canlı çalışma yoktur.
