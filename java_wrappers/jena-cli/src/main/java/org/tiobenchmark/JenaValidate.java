package org.tiobenchmark;

import java.io.File;
import java.io.StringWriter;

import org.apache.jena.graph.Graph;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFFormat;
import org.apache.jena.shacl.ShaclValidator;
import org.apache.jena.shacl.Shapes;
import org.apache.jena.shacl.ValidationReport;

/**
 * Apache Jena SHACL validation CLI for tio-benchmark.
 *
 * Pre-loads data and shapes graphs, applies the generic SHACL-AF
 * {@link SparqlTargetTypePolyfill} so parameterised {@code sh:SPARQLTargetType}
 * instances validate correctly, then times shape parsing + validation.
 *
 * Output: JSON to stdout: {"conforms":true/false,"violations":N,"validation_ms":...}
 */
public class JenaValidate {

    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java -jar jena-shacl-cli.jar <data.ttl> <shapes.ttl>");
            System.exit(1);
        }

        String dataPath = args[0];
        String shapesPath = args[1];

        try {
            // Pre-load graphs (NOT timed — excludes I/O from measurement)
            Graph dataGraph = RDFDataMgr.loadGraph(dataPath);
            Graph shapesGraph = RDFDataMgr.loadGraph(shapesPath);

            // Polyfill sh:SPARQLTargetType — also NOT timed since it is
            // semantically identical to what AF-compliant validators do
            // internally.
            SparqlTargetTypePolyfill.apply(shapesGraph);

            // Time shape parsing + validation
            long t0 = System.nanoTime();
            Shapes shapes = Shapes.parse(shapesGraph);
            ValidationReport report = ShaclValidator.get().validate(shapes, dataGraph);
            long elapsed = System.nanoTime() - t0;
            double validationMs = elapsed / 1_000_000.0;

            boolean conforms = report.conforms();
            int violations = report.getEntries().size();

            // Serialize full SHACL report to Turtle
            StringWriter reportWriter = new StringWriter();
            RDFDataMgr.write(reportWriter, report.getModel(), RDFFormat.TURTLE_PRETTY);
            String reportTurtle = reportWriter.toString()
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");

            System.out.printf(
                "{\"conforms\":%s,\"violations\":%d,\"validation_ms\":%.2f,\"report\":\"%s\"}%n",
                conforms, violations, validationMs, reportTurtle
            );

        } catch (Exception e) {
            String msg = e.getMessage() != null ? e.getMessage() : e.getClass().getName();
            System.out.printf(
                "{\"conforms\":false,\"violations\":-1,\"validation_ms\":0,\"error\":\"%s\"}%n",
                msg.replace("\"", "\\\"").replace("\n", " ")
            );
            System.exit(1);
        }
    }
}
