CREATE TABLE "learning_day" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"date" date NOT NULL UNIQUE,
	"hebrew_date" text,
	"track_1_perakim" jsonb NOT NULL,
	"track_3_perakim" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "content_item" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"learning_day_id" uuid,
	"content_type" text NOT NULL,
	"sefer" text NOT NULL,
	"perek" integer NOT NULL,
	"halacha_start" integer,
	"halacha_end" integer,
	"title" text,
	"content" jsonb NOT NULL,
	"image_url" text,
	"thumbnail_url" text,
	"status" text DEFAULT 'draft',
	"reviewed_by" text[],
	"review_notes" text,
	"published_at" timestamp with time zone,
	"generation_model" text,
	"sort_order" integer DEFAULT 0,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "sichos_reference" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"sefer" text NOT NULL,
	"perek" integer NOT NULL,
	"halacha" integer NOT NULL,
	"source_volume" text NOT NULL,
	"source_page" text,
	"source_url" text,
	"excerpt" text,
	"excerpt_he" text,
	"created_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "user_preference" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"device_id" text UNIQUE,
	"track" text DEFAULT '3-perek',
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "whatsapp_subscriber" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"phone_hash" text NOT NULL UNIQUE,
	"track" text DEFAULT '3-perek',
	"subscribed_at" timestamp with time zone DEFAULT now(),
	"unsubscribed_at" timestamp with time zone,
	"status" text DEFAULT 'active'
);
--> statement-breakpoint
CREATE TABLE "share_event" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
	"content_item_id" uuid,
	"platform" text,
	"created_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
ALTER TABLE "content_item" ADD CONSTRAINT "content_item_learning_day_id_learning_day_id_fkey" FOREIGN KEY ("learning_day_id") REFERENCES "learning_day"("id");--> statement-breakpoint
ALTER TABLE "share_event" ADD CONSTRAINT "share_event_content_item_id_content_item_id_fkey" FOREIGN KEY ("content_item_id") REFERENCES "content_item"("id");