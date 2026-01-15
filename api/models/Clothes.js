const mongoose = require('mongoose');

const clothesSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true
  },
  category: {
    type: String,
    required: true
  },
  size: {
    type: String,
    required: false
  },
  color: {
    type: String,
    required: false
  },
  price: {
    type: Number,
    required: false
  },
  description: {
    type: String,
    required: false
  },
  inStock: {
    type: Boolean,
    default: true
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Clothes', clothesSchema);
