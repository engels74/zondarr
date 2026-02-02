<script lang="ts">
	import AdminLayout from '../../routes/(admin)/+layout.svelte';
</script>

<AdminLayout>
	{#snippet children()}
		<div data-testid="test-content">Test Content</div>
	{/snippet}
</AdminLayout>
