import React, { useState } from 'react';
import { View, Text, TextInput, Button, FlatList, TouchableOpacity, StyleSheet, SafeAreaView, ScrollView } from 'react-native';
import { useApp } from '../utils/store';
import { SharedItem, Group } from '../types';

// Simple Navigation Controller for MVP (No React Navigation dependency required for this demo, 
// though recommended for real app)
export default function MainNavigator() {
  const { user } = useApp();
  const [currentScreen, setCurrentScreen] = useState<'Login' | 'GroupList' | 'GroupDetail' | 'AddItem'>('Login');
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);

  if (!user) {
    return <LoginScreen />;
  }

  const navigateToGroup = (groupId: string) => {
    setActiveGroupId(groupId);
    setCurrentScreen('GroupDetail');
  };

  const goBack = () => {
      if (currentScreen === 'AddItem') setCurrentScreen('GroupDetail');
      else if (currentScreen === 'GroupDetail') setCurrentScreen('GroupList');
  }

  switch (currentScreen) {
    case 'GroupList':
      return <GroupListScreen onSelectGroup={navigateToGroup} />;
    case 'GroupDetail':
      if (!activeGroupId) return <GroupListScreen onSelectGroup={navigateToGroup} />;
      return (
        <GroupDetailScreen 
          groupId={activeGroupId} 
          onAddItem={() => setCurrentScreen('AddItem')} 
          onBack={goBack}
        />
      );
    case 'AddItem':
        return <AddItemScreen groupId={activeGroupId!} onBack={goBack} />;
    default:
      return <GroupListScreen onSelectGroup={navigateToGroup} />;
  }
}

// --- Screens ---

function LoginScreen() {
  const { login } = useApp();
  const [name, setName] = useState('');

  return (
    <View style={styles.centerContainer}>
      <Text style={styles.title}>Sharable</Text>
      <Text style={styles.subtitle}>Split bulk items easily.</Text>
      <TextInput
        style={styles.input}
        placeholder="Enter your name"
        value={name}
        onChangeText={setName}
      />
      <Button title="Start" onPress={() => name && login(name)} />
    </View>
  );
}

function GroupListScreen({ onSelectGroup }: { onSelectGroup: (id: string) => void }) {
  const { groups, createGroup, user } = useApp();
  const [newGroupName, setNewGroupName] = useState('');

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Groups</Text>
        <Text style={styles.userBadge}>{user?.name}</Text>
      </View>
      
      <View style={styles.createSection}>
        <TextInput 
            style={styles.input} 
            placeholder="New Group Name (e.g. Costco Run)" 
            value={newGroupName}
            onChangeText={setNewGroupName}
        />
        <Button title="Create Group" onPress={() => {
            if (newGroupName) {
                createGroup(newGroupName);
                setNewGroupName('');
            }
        }} />
      </View>

      <FlatList
        data={groups}
        keyExtractor={g => g.id}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => onSelectGroup(item.id)}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardSubtitle}>Code: {item.inviteCode}</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={styles.emptyText}>No groups yet. Create one!</Text>}
      />
    </SafeAreaView>
  );
}

function GroupDetailScreen({ groupId, onAddItem, onBack }: { groupId: string, onAddItem: () => void, onBack: () => void }) {
  const { items, groups, toggleClaim, user } = useApp();
  const group = groups.find(g => g.id === groupId);
  const groupItems = items.filter(i => i.groupId === groupId);

  if (!group) return <Text>Group not found</Text>;

  const calculateRemaining = (item: SharedItem) => {
    const claimed = item.claims.reduce((acc, c) => acc + c.quantity, 0);
    return item.totalQuantity - claimed;
  };

  const calculateMyCost = (item: SharedItem) => {
      const myClaim = item.claims.find(c => c.userId === user?.id);
      if (!myClaim) return 0;
      const unitPrice = item.totalPrice / item.totalQuantity;
      return unitPrice * myClaim.quantity;
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}><Text style={styles.backButton}>Back</Text></TouchableOpacity>
        <Text style={styles.headerTitle}>{group.name}</Text>
         <Button title="Add Item" onPress={onAddItem} />
      </View>

      <FlatList
        data={groupItems}
        keyExtractor={i => i.id}
        contentContainerStyle={{ paddingBottom: 100 }}
        renderItem={({ item }) => {
            const remaining = calculateRemaining(item);
            const myClaim = item.claims.find(c => c.userId === user?.id);
            const myQty = myClaim ? myClaim.quantity : 0;
            const unitPrice = item.totalPrice / item.totalQuantity;

            return (
                <View style={styles.itemCard}>
                    <View style={styles.itemRow}>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.itemTitle}>{item.name}</Text>
                            <Text style={styles.itemPrice}>${item.totalPrice.toFixed(2)} total • ${(unitPrice).toFixed(2)} / {item.unitName || 'unit'}</Text>
                        </View>
                        <View style={styles.itemStatus}>
                            <Text style={{ color: remaining < 0 ? 'red' : 'green', fontWeight: 'bold' }}>
                                {remaining} left
                            </Text>
                        </View>
                    </View>
                    
                    {/* One-Tap Interactions */}
                    <View style={styles.actionRow}>
                        <View style={styles.counter}>
                           <Button title="-" onPress={() => toggleClaim(item.id, Math.max(0, myQty - 1))} />
                           <Text style={styles.counterText}>{myQty}</Text>
                           <Button title="+" onPress={() => toggleClaim(item.id, myQty + 1)} />
                        </View>
                        <Text style={styles.costText}>
                            You owe: ${(calculateMyCost(item)).toFixed(2)}
                        </Text>
                    </View>
                </View>
            );
        }}
        ListEmptyComponent={<Text style={styles.emptyText}>No items yet. Tap 'Add Item' to start.</Text>}
      />
    </SafeAreaView>
  );
}

function AddItemScreen({ groupId, onBack }: { groupId: string, onBack: () => void }) {
    const { addItem, user } = useApp();
    const [name, setName] = useState('');
    const [price, setPrice] = useState('');
    const [qty, setQty] = useState('');
    const [unit, setUnit] = useState('');

    const handleCreate = () => {
        if (!name || !price || !qty) return;
        addItem({
            groupId,
            createdBy: user!.id,
            name,
            totalPrice: parseFloat(price),
            totalQuantity: parseInt(qty),
            unitName: unit || 'unit'
        });
        onBack();
    };

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={onBack}><Text style={styles.backButton}>Cancel</Text></TouchableOpacity>
                <Text style={styles.headerTitle}>Add Generic Item</Text>
            </View>
            <View style={styles.form}>
                <Text style={styles.label}>Item Name</Text>
                <TextInput style={styles.input} placeholder="e.g. Toilet Paper" value={name} onChangeText={setName} />
                
                <Text style={styles.label}>Total Price ($)</Text>
                <TextInput style={styles.input} placeholder="24.99" keyboardType="numeric" value={price} onChangeText={setPrice} />
                
                <View style={styles.row}>
                    <View style={{ flex: 1, marginRight: 10 }}>
                        <Text style={styles.label}>Total Qty</Text>
                        <TextInput style={styles.input} placeholder="30" keyboardType="numeric" value={qty} onChangeText={setQty} />
                    </View>
                    <View style={{ flex: 1 }}>
                        <Text style={styles.label}>Unit Name</Text>
                        <TextInput style={styles.input} placeholder="rolls" value={unit} onChangeText={setUnit} />
                    </View>
                </View>

                <Button title="Post Item" onPress={handleCreate} />
            </View>
        </SafeAreaView>
    );
}

// --- Styles ---
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f2f2f7' },
  centerContainer: { flex: 1, justifyContent: 'center', padding: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#ddd' },
  headerTitle: { fontSize: 20, fontWeight: 'bold' },
  card: { backgroundColor: '#fff', padding: 16, marginHorizontal: 16, marginTop: 12, borderRadius: 12 },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  cardSubtitle: { color: '#666', marginTop: 4 },
  title: { fontSize: 32, fontWeight: 'bold', textAlign: 'center', marginBottom: 8 },
  subtitle: { fontSize: 18, color: '#666', textAlign: 'center', marginBottom: 32 },
  input: { backgroundColor: '#fff', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', marginBottom: 12, fontSize: 16 },
  createSection: { padding: 16 },
  userBadge: { color: '#007AFF', fontWeight: 'bold' },
  emptyText: { textAlign: 'center', marginTop: 40, color: '#999' },
  backButton: { color: '#007AFF', fontSize: 16 },
  
  // Item Card
  itemCard: { backgroundColor: '#fff', padding: 16, marginHorizontal: 16, marginTop: 12, borderRadius: 12 },
  itemRow: { flexDirection: 'row', justifyContent: 'space-between' },
  itemTitle: { fontSize: 18, fontWeight: '600' },
  itemPrice: { color: '#666' },
  itemStatus: { justifyContent: 'center' },
  
  actionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#eee' },
  counter: { flexDirection: 'row', alignItems: 'center' },
  counterText: { fontSize: 18, fontWeight: 'bold', marginHorizontal: 12, minWidth: 20, textAlign: 'center' },
  costText: { fontWeight: '600', color: '#007AFF' },
  
  form: { padding: 20 },
  label: { marginBottom: 4, color: '#333', fontWeight: '600' },
  row: { flexDirection: 'row' },
});
