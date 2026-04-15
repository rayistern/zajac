CREATE TABLE "bookmark" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"device_id" text NOT NULL,
	"content_item_id" uuid NOT NULL,
	"created_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "sefer_hamitzvos_reference" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"rambam_ref" text NOT NULL,
	"mitzvah_type" text NOT NULL,
	"mitzvah_number" integer NOT NULL,
	"title_he" text,
	"title_en" text,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "feature_flag" (
	"key" text PRIMARY KEY,
	"value" jsonb NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX "bookmark_device_content_unique" ON "bookmark" ("device_id","content_item_id");--> statement-breakpoint
CREATE UNIQUE INDEX "sefer_hamitzvos_ref_unique" ON "sefer_hamitzvos_reference" ("rambam_ref","mitzvah_type","mitzvah_number");--> statement-breakpoint
ALTER TABLE "bookmark" ADD CONSTRAINT "bookmark_content_item_id_content_item_id_fkey" FOREIGN KEY ("content_item_id") REFERENCES "content_item"("id") ON DELETE CASCADE;