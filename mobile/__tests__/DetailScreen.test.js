import 'react-native';
import React from 'react';
import DetailScreen from '../screens/DetailScreen';
import {render} from '@testing-library/react-native';

const mockRoute = {
  params: {
    item: {
      id: 1,
      name: 'Test Item',
      price: 49.99,
      category: 'TestCategory',
      description: 'This is a test item description',
    },
  },
};

const mockNavigation = {
  navigate: jest.fn(),
};

describe('DetailScreen', () => {
  it('renders item details correctly', () => {
    const {getByText} = render(
      <DetailScreen route={mockRoute} navigation={mockNavigation} />,
    );

    expect(getByText('Test Item')).toBeTruthy();
    expect(getByText('TestCategory')).toBeTruthy();
    expect(getByText('$49.99')).toBeTruthy();
    expect(getByText('This is a test item description')).toBeTruthy();
  });

  it('renders Add to Cart button', () => {
    const {getByText} = render(
      <DetailScreen route={mockRoute} navigation={mockNavigation} />,
    );

    expect(getByText('Add to Cart')).toBeTruthy();
  });
});
