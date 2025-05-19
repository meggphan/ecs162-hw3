<script lang="ts">
import { onMount } from 'svelte';

interface Article {
  _id: string;
  web_url: string;
  snippet: string;
  headline: { main: string };
  multimedia: { default?: { url: string } };
}

let articles: Article[] = [];
let user: any = null;
let apiKey = '';
let loading = true;
let error: string | null = null;
let comments: Record<string, any[]> = {};
let newComment: Record<string, string> = {};

const getImageUrl = (article: Article): string | null => {
  return article.multimedia?.default?.url ?? null;
};

function formatDate(): string {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
}

onMount(async () => {
  try {
    const keyRes = await fetch('/api/key');
    apiKey = (await keyRes.json()).apiKey;
    await fetchUser();
    await fetchArticles();
  } catch (e) {
    error = 'Failed to load.';
  } finally {
    loading = false;
  }
});

async function fetchUser() {
  const res = await fetch('/api/user');
  if (res.ok) user = await res.json();
}

async function fetchArticles() {
  const res = await fetch('/api/articles');
  const data = await res.json();
  articles = data.response.docs;
  console.log('Fetched article:', articles[0]);
  for (const article of articles) await fetchComments(article._id);
}

async function fetchComments(articleId: string) {
  const res = await fetch(`/api/comments?article_id=${articleId}`);
  comments[articleId] = await res.json();
}

async function postComment(articleId: string) {
  const res = await fetch('/api/comments', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ article_id: articleId, text: newComment[articleId] })
  });
  if (res.ok) {
    newComment[articleId] = '';
    await fetchComments(articleId);
  }
}

function login() { window.location.href = '/login'; }
function logout() { window.location.href = '/logout'; }
</script>

<div id="app">
  <header>
    <div class="header-left">
      <div>{formatDate()}</div>
      <div>Today's Paper</div>
    </div>
    <div class="Center-Title">
      <img src="/src/assets/static/NYT.svg" width="500" alt="The New York Times" />
    </div>
    <div class="header-right">
      {#if user}
        <span>{user.email}</span>
        <button on:click={logout}>Logout</button>
      {:else}
        <button on:click={login}>Login</button>
      {/if}
    </div>
  </header>

  <main>
    {#if loading}
      <p>Loading...</p>
    {:else if error}
      <p>{error}</p>
    {:else}
      {#each articles.slice(0, 6) as article, i}
        <section class="card">
          <a href={article.web_url} target="_blank">
            <h2>{article.headline.main}</h2>
          </a>
          {#if getImageUrl(article)}
            <img src={getImageUrl(article)} alt="article image" style="max-width: 100%; margin: 1rem 0" />
          {/if}
          <p>{article.snippet}</p>

          <div class="comments">
            <h3>Comments</h3>
            {#each comments[article._id] || [] as comment}
              <div>
                {#if comment.removed}
                  <p><em>COMMENT REMOVED BY MODERATOR</em></p>
                {:else}
                  <p><strong>{comment.user_email}</strong>: {comment.text}</p>
                {/if}
              </div>
            {/each}

            {#if user}
              <textarea bind:value={newComment[article._id]} placeholder="Write a comment..." style="width: 100%; margin-top: 0.5rem;"></textarea>
              <button on:click={() => postComment(article._id)}>Post</button>
            {/if}
          </div>
        </section>
      {/each}
    {/if}
  </main>
</div>