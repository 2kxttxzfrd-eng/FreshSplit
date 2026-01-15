export interface User {
  id: string;
  name: string;
  avatarUrl?: string; // Optional for MVP
}

export interface Group {
  id: string;
  name: string;
  inviteCode: string; // Simple unique code for MVP sharing
  members: string[]; // User IDs
}

export interface Claim {
  userId: string;
  quantity: number;
}

export interface SharedItem {
  id: string;
  groupId: string;
  createdBy: string; // User ID
  name: string;
  totalQuantity: number;
  unitName?: string; // e.g., "rolls", "cans"
  totalPrice: number;
  photoUrl?: string;
  notes?: string;
  claims: Claim[];
  createdAt: number;
}
