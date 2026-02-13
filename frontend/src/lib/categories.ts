import { Category } from "@/types/event";

export const CATEGORY_FALLBACK_COLOR = "#6B7280";

export function categoryColor(category: Category | null): string {
  return category?.color ?? CATEGORY_FALLBACK_COLOR;
}

export function sortedCategories(categories: Category[]): Category[] {
  return [...categories].sort((a, b) => a.name.localeCompare(b.name));
}
