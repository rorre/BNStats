-- upgrade --
ALTER TABLE "nomination" ALTER COLUMN "user_id" DROP NOT NULL;
ALTER TABLE "nomination"
    DROP CONSTRAINT nomination_user_id_fkey,
    ADD CONSTRAINT nomination_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public."user" ("osuId") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL;
-- downgrade --
ALTER TABLE "nomination" ALTER COLUMN "user_id" SET NOT NULL;
ALTER TABLE "nomination"
    DROP CONSTRAINT nomination_user_id_fkey,
    ADD CONSTRAINT nomination_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public."user" ("osuId") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE;