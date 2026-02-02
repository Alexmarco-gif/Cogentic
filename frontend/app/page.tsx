export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">Welcome to Cogent AI</h1>
        <p className="text-gray-600 mb-8">Authentication is configured</p>
        <a
          href="/auth-test"
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-block"
        >
          Test Authentication
        </a>
      </div>
    </main>
  )
}
