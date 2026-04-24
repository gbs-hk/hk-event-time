export type Category = {
  id: number;
  name: string;
  slug: string;
  color: string;
  icon: string;
};

export type Source = {
  id: number;
  name: string;
  base_url: string;
};

export type EventItem = {
  id: number;
  name: string;
  start_datetime: string;
  end_datetime: string | null;
  location: string | null;
  organizer: string | null;
  description: string | null;
  ticket_url: string | null;
  discount_text: string | null;
  discount_url: string | null;
  tags: string[];
  last_seen_at: string;
  category: Category | null;
  source: Source;
};
