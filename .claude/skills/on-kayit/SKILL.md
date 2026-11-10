---
name: on-kayit
description: QuantBIST'te herhangi bir ölçüm, backtest ya da araştırma çalıştırılmadan önce hipotezi, ölçütü ve deneme sayısını DECISIONS.md'ye yeni bir K numarasıyla yazdırır. Kayıt yoksa ölçüme izin vermez.
---

# Ön kayıt

Ölçümden önce, sonuca bakmadan:

1. `docs/DECISIONS.md`'deki en büyük K numarasını bul; yenisi bir fazlası.
2. En üste (tarih başlığı altında) şu alanlarla yaz:
   - **Soru / hipotez:** tek cümle, ölçülebilir.
   - **Veri:** kaynak, dönem, evren; holdout'a (`HOLDOUT_START`) dokunuluyor mu (dokunulmaz, ancak ayrı onaylı ileri testte).
   - **Ölçüt:** karar kuralı ve eşik; "geçti/geçmedi/ölçülemedi" tablosu.
   - **Deneme sayısı:** bu ve önceki denemeler (çoklu test düzeltmesi, DSR için N).
   - **Beklenti:** ölçümden önce yazılan tahmin.
   - **Reddedilen:** sonuca göre ölçütü, pencereyi ya da parametreyi değiştirmek.
3. Commit et (dal üzerinden), sonra ölçümü çalıştır. Kayıt commit'i ölçüm commit'inden önce olmalı.
4. Sonuç aynı K'nın altına "Sonuç" olarak eklenir; ölçüt değiştirilmez. Başarısız ölçüm başka ayarla yeniden çalıştırılmaz.

K-79 dondurma parçaları, K-78/K-80 kuralları, holdout ve 03.02.2027 ileri testi kullanıcının ayrı onayı olmadan değişmez.
