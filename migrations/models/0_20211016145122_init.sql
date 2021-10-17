-- upgrade --
CREATE TABLE IF NOT EXISTS "beatmap" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "beatmapset_id" INT NOT NULL,
    "beatmap_id" INT NOT NULL,
    "approved" INT NOT NULL,
    "total_length" INT NOT NULL,
    "hit_length" INT NOT NULL,
    "mode" INT NOT NULL,
    "artist" VARCHAR(255) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "creator" VARCHAR(255) NOT NULL,
    "creator_id" INT NOT NULL  DEFAULT 0,
    "tags" TEXT NOT NULL,
    "genre_id" INT NOT NULL,
    "language_id" INT NOT NULL,
    "difficultyrating" DOUBLE PRECISION NOT NULL
);
COMMENT ON TABLE "beatmap" IS 'osu!beatmap representation.';
CREATE TABLE IF NOT EXISTS "reset" (
    "id" TEXT NOT NULL  PRIMARY KEY,
    "beatmapsetId" INT NOT NULL,
    "userId" INT NOT NULL,
    "artistTitle" TEXT NOT NULL,
    "creatorId" INT,
    "creatorName" TEXT,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "content" TEXT,
    "discussionId" INT,
    "obviousness" INT NOT NULL  DEFAULT 0,
    "severity" INT NOT NULL  DEFAULT 0,
    "type" VARCHAR(50) NOT NULL
);
CREATE TABLE IF NOT EXISTS "user" (
    "_id" TEXT NOT NULL,
    "osuId" SERIAL NOT NULL PRIMARY KEY,
    "username" TEXT NOT NULL,
    "modesInfo" JSONB NOT NULL,
    "isNat" BOOL NOT NULL,
    "isBn" BOOL NOT NULL,
    "modes" JSONB NOT NULL,
    "last_updated" TIMESTAMPTZ,
    "genre_favor" JSONB,
    "lang_favor" JSONB,
    "topdiff_favor" JSONB,
    "size_favor" VARCHAR(20),
    "length_favor" VARCHAR(20),
    "avg_length" INT,
    "avg_diffs" INT
);
CREATE TABLE IF NOT EXISTS "nomination" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "beatmapsetId" INT NOT NULL,
    "userId" INT NOT NULL,
    "artistTitle" TEXT NOT NULL,
    "creatorId" INT,
    "creatorName" TEXT,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "as_modes" JSONB,
    "ambiguous_mode" BOOL NOT NULL  DEFAULT False,
    "score" JSONB NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("osuId") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(20) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "user_reset" (
    "reset_id" TEXT NOT NULL REFERENCES "reset" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("osuId") ON DELETE CASCADE
);
