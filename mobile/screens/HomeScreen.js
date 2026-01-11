import React, {useState, useEffect} from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
} from 'react-native';
import axios from 'axios';

const HomeScreen = ({navigation}) => {
  const [clothes, setClothes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClothes();
  }, []);

  const fetchClothes = async () => {
    try {
      const response = await axios.get('http://localhost:3000/clothes');
      setClothes(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching clothes:', error);
      setLoading(false);
      Alert.alert(
        'Error',
        'Failed to fetch clothing items. Please check if the API is running.',
      );
      // Set mock data for demo purposes
      setClothes([
        {
          id: 1,
          name: 'Classic T-Shirt',
          price: 29.99,
          category: 'Shirts',
          description: 'Comfortable cotton t-shirt',
        },
        {
          id: 2,
          name: 'Denim Jeans',
          price: 79.99,
          category: 'Pants',
          description: 'Classic blue denim jeans',
        },
        {
          id: 3,
          name: 'Sneakers',
          price: 99.99,
          category: 'Shoes',
          description: 'Comfortable running sneakers',
        },
        {
          id: 4,
          name: 'Jacket',
          price: 149.99,
          category: 'Outerwear',
          description: 'Warm winter jacket',
        },
        {
          id: 5,
          name: 'Summer Dress',
          price: 59.99,
          category: 'Dresses',
          description: 'Light and breezy summer dress',
        },
      ]);
    }
  };

  const renderItem = ({item}) => (
    <TouchableOpacity
      style={styles.itemContainer}
      onPress={() => navigation.navigate('Detail', {item})}>
      <Image
        source={{
          uri: `https://source.unsplash.com/300x200/?${item.category.toLowerCase()},fashion`,
        }}
        style={styles.itemImage}
      />
      <View style={styles.itemDetails}>
        <Text style={styles.itemName}>{item.name}</Text>
        <Text style={styles.itemCategory}>{item.category}</Text>
        <Text style={styles.itemPrice}>${item.price.toFixed(2)}</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading clothes...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={clothes}
        renderItem={renderItem}
        keyExtractor={item => item.id.toString()}
        contentContainerStyle={styles.listContainer}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  listContainer: {
    padding: 10,
  },
  itemContainer: {
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    overflow: 'hidden',
  },
  itemImage: {
    width: '100%',
    height: 200,
    resizeMode: 'cover',
  },
  itemDetails: {
    padding: 15,
  },
  itemName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
  },
  itemCategory: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  itemPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2196F3',
  },
});

export default HomeScreen;
