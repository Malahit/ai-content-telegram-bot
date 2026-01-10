const express = require('express');
const router = express.Router();
const Clothes = require('../models/Clothes');

// Default data for clothes
const defaultClothes = [
  {
    id: 1,
    name: 'Classic T-Shirt',
    category: 'Tops',
    size: 'M',
    color: 'Blue',
    price: 29.99,
    description: 'Comfortable cotton t-shirt',
    inStock: true
  },
  {
    id: 2,
    name: 'Denim Jeans',
    category: 'Bottoms',
    size: 'L',
    color: 'Dark Blue',
    price: 79.99,
    description: 'Classic fit denim jeans',
    inStock: true
  },
  {
    id: 3,
    name: 'Summer Dress',
    category: 'Dresses',
    size: 'S',
    color: 'Floral',
    price: 59.99,
    description: 'Light and breezy summer dress',
    inStock: false
  },
  {
    id: 4,
    name: 'Hoodie',
    category: 'Tops',
    size: 'XL',
    color: 'Gray',
    price: 49.99,
    description: 'Warm and cozy hoodie',
    inStock: true
  }
];

// GET /clothes - Return all clothes
router.get('/', async (req, res) => {
  try {
    // Try to fetch from database first
    const clothes = await Clothes.find();
    
    // If database is empty, return default data
    if (clothes.length === 0) {
      return res.json(defaultClothes);
    }
    
    res.json(clothes);
  } catch (error) {
    console.error('Error fetching clothes:', error);
    // If database error, return default data
    res.json(defaultClothes);
  }
});

module.exports = router;
