import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Pipeline from './pages/Pipeline'
import Analytics from './pages/Analytics'
import Direction from './pages/Direction'
import Urgences from './pages/Urgences'
import Parametres from './pages/Parametres'
import Guide from './pages/Guide'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Pipeline />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="direction" element={<Direction />} />
        <Route path="urgences" element={<Urgences />} />
        <Route path="parametres" element={<Parametres />} />
        <Route path="guide" element={<Guide />} />
      </Route>
    </Routes>
  )
}
