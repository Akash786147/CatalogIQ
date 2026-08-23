import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import ReviewQueue from "@/pages/ReviewQueue";
import RowDetail from "@/pages/RowDetail";
import SearchProof from "@/pages/SearchProof";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="review" element={<ReviewQueue />} />
        <Route path="review/:rowId" element={<RowDetail />} />
        <Route path="search" element={<SearchProof />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
