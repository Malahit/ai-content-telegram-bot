import 'react-native';
import React from 'react';
import HomeScreen from '../screens/HomeScreen';
import {render, waitFor} from '@testing-library/react-native';
import axios from 'axios';

jest.mock('axios');

const mockNavigation = {
  navigate: jest.fn(),
};

describe('HomeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    const {getByText} = render(<HomeScreen navigation={mockNavigation} />);
    expect(getByText('Loading clothes...')).toBeTruthy();
  });

  it('fetches and displays clothes from API', async () => {
    const mockClothes = [
      {id: 1, name: 'Test Shirt', price: 29.99, category: 'Shirts', description: 'Test'},
    ];
    axios.get.mockResolvedValue({data: mockClothes});

    const {getByText} = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText('Test Shirt')).toBeTruthy();
    });
  });

  it('displays mock data when API fails', async () => {
    axios.get.mockRejectedValue(new Error('API Error'));

    const {getByText} = render(<HomeScreen navigation={mockNavigation} />);

    await waitFor(() => {
      expect(getByText('Classic T-Shirt')).toBeTruthy();
    });
  });
});
