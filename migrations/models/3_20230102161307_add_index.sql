-- upgrade --
CREATE INDEX "idx_beatmap_beatmap_06ef7a" ON "beatmap" ("beatmapset_id");
CREATE INDEX "idx_nomination_userId_483bfd" ON "nomination" ("userId");
CREATE INDEX "idx_user_isBn_05bd8a" ON "user" ("isBn");
CREATE INDEX "idx_user_isNat_0f5525" ON "user" ("isNat");
-- downgrade --
DROP INDEX "idx_nomination_userId_483bfd";
DROP INDEX "idx_beatmap_beatmap_06ef7a";
DROP INDEX "idx_user_isNat_0f5525";
DROP INDEX "idx_user_isBn_05bd8a";
