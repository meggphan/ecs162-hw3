import { test, describe, it, expect, vi, beforeEach} from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import App from './App.svelte';

describe('testing if server returns api key', () => {
  it('should return an object with apiKey property', async () => {
    const response = await fetch('http://localhost:8000/api/key');
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('apiKey');
    expect(data.apiKey.length).toBeGreaterThan(0);
  });
});

describe('App.svelte', () => {
  it('displays fake article content', async () => {
    global.fetch = vi.fn((url: string) => {
      if(url.includes('/api/key')) {
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve({ apiKey: 'test-key' })
        });
      }

      if(url.includes('articlesearch')) {
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve({
            status: 'OK',
            response: {
              docs: Array.from({length:6}, (_,i) => ({
                _id: `id-${i}`,
                web_url: `https://nytimes.com/test-article-${i}`,
                headline: { main: `Test Headline ${i}` },
                snippet: `Test Snippet ${i}`,
                multimedia: {
                  caption: '',
                  credit: '',
                  default: {
                    url: 'image/test-image.jpg',
                    width: 100,
                    height: 100           
                  },
                  thumbnail: undefined       
                }
              }))
            }
          })
        });
      }
      return Promise.reject(new Error('Unexpected fetch'));
    }) as any;
    const {getByText} = render(App);
    await waitFor(() => {
      expect(getByText('Test Headline 0')).toBeTruthy();
      expect(getByText('Test Snippet 0')).toBeTruthy();
    });
  });
});


describe('NYT API format', () => {
  it('returns data in expected format', async () => {
    const NYTAPI = {
      response: {
        docs: [
          {
            headline: { main: 'Test Headline' },
            web_url: 'https://nytimes.com/test-article',
            multimedia: [
              { url: 'images/test-image' }
            ],
            abstract: 'blahblahblah',
          }
        ]
      }
    };

    const articles = NYTAPI.response.docs.map(doc => ({
      title: doc.headline.main,
      article_url: doc.web_url,
      multimedia: doc.multimedia.map(m => m.url),
      abstract: doc.abstract
    }));

    const article = articles[0];

    expect(article).toHaveProperty('title');
    expect(typeof article.title).toBe('string');

    expect(article).toHaveProperty('article_url');
    expect(article.article_url).toMatch(/^https?:\/\//);

    expect(article).toHaveProperty('multimedia');
    expect(Array.isArray(article.multimedia)).toBe(true);

    expect(article).toHaveProperty('abstract');
    expect(typeof article.abstract).toBe('string');
  });
});

describe('NYT API query check', () => {
  it('should include "Davis OR Sacramento" in the query string', async () => {
    const fakeKey = 'test-key';

    const fetchSpy = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ response: { docs: [] } }),
      status: 200
    });

    global.fetch = fetchSpy;

    const url = `https://api.nytimes.com/svc/search/v2/articlesearch.json?q=Davis OR Sacramento&api-key=${fakeKey}`;
    await fetch(url);

    const calledUrl = fetchSpy.mock.calls[0][0];

    expect(calledUrl).toContain('q=Davis OR Sacramento');
    expect(calledUrl).toContain('api-key=test-key');
  });
});
