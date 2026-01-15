import React, { createContext, useContext, useState, ReactNode } from 'react';
import { User, Group, SharedItem } from '../types';

// Mock Data
const MOCK_USER: User = { id: 'u1', name: 'You' };

interface AppState {
  user: User | null;
  groups: Group[];
  items: SharedItem[];
  login: (name: string) => void;
  createGroup: (name: string) => void;
  joinGroup: (inviteCode: string) => void;
  addItem: (item: Omit<SharedItem, 'id' | 'createdAt' | 'claims'>) => void;
  toggleClaim: (itemId: string, quantity: number) => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [items, setItems] = useState<SharedItem[]>([]);

  const login = (name: string) => {
    setUser({ id: 'u1', name }); // Mock ID
  };

  const createGroup = (name: string) => {
    const newGroup: Group = {
      id: Math.random().toString(36).substr(2, 9),
      name,
      inviteCode: Math.random().toString(36).substr(2, 6).toUpperCase(),
      members: [user!.id],
    };
    setGroups([...groups, newGroup]);
  };

  const joinGroup = (inviteCode: string) => {
      // Mock join logic
      const groupIndex = groups.findIndex(g => g.inviteCode === inviteCode);
      if (groupIndex > -1) {
          const updatedGroups = [...groups];
          if (!updatedGroups[groupIndex].members.includes(user!.id)) {
             updatedGroups[groupIndex].members.push(user!.id);
             setGroups(updatedGroups);
          }
      }
  };

  const addItem = (itemData: Omit<SharedItem, 'id' | 'createdAt' | 'claims'>) => {
    const newItem: SharedItem = {
      ...itemData,
      id: Math.random().toString(36).substr(2, 9),
      createdAt: Date.now(),
      claims: [],
    };
    setItems([newItem, ...items]);
  };

  const toggleClaim = (itemId: string, quantity: number) => {
    setItems(currentItems => 
      currentItems.map(item => {
        if (item.id !== itemId) return item;

        const existingClaimIndex = item.claims.findIndex(c => c.userId === user!.id);
        let newClaims = [...item.claims];

        if (existingClaimIndex > -1) {
            // Edit or remove if quantity is 0 (though UI might handle 0 differently)
            if (quantity === 0) {
                 newClaims = newClaims.filter((_, i) => i !== existingClaimIndex);
            } else {
                 newClaims[existingClaimIndex] = { ...newClaims[existingClaimIndex], quantity };
            }
        } else if (quantity > 0) {
            // New claim
            newClaims.push({ userId: user!.id, quantity });
        }

        return { ...item, claims: newClaims };
      })
    );
  };

  return (
    <AppContext.Provider value={{ user, groups, items, login, createGroup, joinGroup, addItem, toggleClaim }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
};
