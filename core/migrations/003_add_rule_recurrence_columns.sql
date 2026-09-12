ALTER TABLE rules ADD COLUMN "rrule" TEXT;
ALTER TABLE rules ADD COLUMN "dtstart" TEXT;
ALTER TABLE rules ADD COLUMN "exclude_dates" JSON;
