import { ArchitectureFlow } from "@/components/architecture-flow";
import { Assistant } from "@/components/assistant";
import { Clouds } from "@/components/clouds";
import { Configuration } from "@/components/configuration";
import { Deliverables } from "@/components/deliverables";
import { Events } from "@/components/events";
import { Footer } from "@/components/footer";
import { Hero } from "@/components/hero";
import { Integration } from "@/components/integration";
import { Interview } from "@/components/interview";
import { Lessons } from "@/components/lessons";
import { Metrics } from "@/components/metrics";
import { Nav } from "@/components/nav";
import { Problem } from "@/components/problem";
import { Reliability } from "@/components/reliability";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Problem />
        <ArchitectureFlow />
        <Deliverables />
        <Clouds />
        <Configuration />
        <Integration />
        <Events />
        <Assistant />
        <Reliability />
        <Metrics />
        <Interview />
        <Lessons />
      </main>
      <Footer />
    </>
  );
}
